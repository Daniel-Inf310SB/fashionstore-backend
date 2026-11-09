"""Scope FashionStore commercial root entities to a single tenant.

Revision ID: d7e2b9a13f60
Revises: c4f1a9b72d60

Expand first: nullable tenant_id allows existing endpoints to continue during transition.
Do not onboard another tenant until every relevant service validates tenant ownership.
"""
from alembic import op
import sqlalchemy as sa

revision = "d7e2b9a13f60"
down_revision = "c4f1a9b72d60"
branch_labels = None
depends_on = None

TABLES = ("categories", "products", "suppliers", "collections", "promotions", "orders", "sales", "reservations")
SCOPED_UNIQUES = {"categories": "name", "products": "code", "suppliers": "nit", "collections": "name"}


def upgrade():
    conn = op.get_bind()
    # This migration is for the existing SINGLE-tenant FashionStore installation only.
    tenants = conn.execute(sa.text("SELECT id FROM tenants ORDER BY id")).scalars().all()
    if len(tenants) != 1:
        raise RuntimeError("Expected exactly one existing tenant for backfill; migrate tenant ownership manually.")
    tenant_id = tenants[0]
    # Reject inconsistent historical ownership before modifying anything.
    for table in ("orders", "sales", "reservations"):
        bad = conn.execute(sa.text(f"""SELECT count(*) FROM {table} t
            JOIN branches b ON b.id = t.branch_id
            WHERE b.tenant_id IS DISTINCT FROM :tenant_id"""), {"tenant_id": tenant_id}).scalar_one()
        if bad:
            raise RuntimeError(f"{table}: some branches do not belong to initial tenant")
    for table in TABLES:
        op.add_column(table, sa.Column("tenant_id", sa.Integer(), nullable=True))
        op.create_index(f"ix_{table}_tenant_id", table, ["tenant_id"])
        op.create_foreign_key(f"fk_{table}_tenant_id_tenants", table, "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT")
        conn.execute(sa.text(f"UPDATE {table} SET tenant_id = :tenant_id WHERE tenant_id IS NULL"), {"tenant_id": tenant_id})
    # Replace global uniqueness by (tenant_id, natural key).
    # Original unique constraints may be created as unique indexes by SQLAlchemy.
    for table, col in SCOPED_UNIQUES.items():
        # Drop only the known single-column unique index; keep ordinary lookup indexes intact.
        inspector = sa.inspect(conn)
        for ix in inspector.get_indexes(table):
            if ix.get("unique") and ix.get("column_names") == [col]:
                op.drop_index(ix["name"], table_name=table)
        for uq in inspector.get_unique_constraints(table):
            if uq.get("column_names") == [col]:
                op.drop_constraint(uq["name"], table, type_="unique")
        op.create_unique_constraint(f"uq_{table}_tenant_{col}", table, ["tenant_id", col])


def downgrade():
    conn = op.get_bind()
    # Global uniqueness cannot be restored if multiple companies share natural keys.
    # Perform preflight before dropping scoped constraints.
    for table, col in SCOPED_UNIQUES.items():
        duplicates = conn.execute(sa.text(f"SELECT COUNT(*) FROM (SELECT {col} FROM {table} GROUP BY {col} HAVING COUNT(*) > 1) q")).scalar_one()
        if duplicates:
            raise RuntimeError(f"Cannot downgrade {table}: duplicate {col} across tenants")
    for table, col in SCOPED_UNIQUES.items():
        op.drop_constraint(f"uq_{table}_tenant_{col}", table, type_="unique")
        op.create_index(f"ix_{table}_{col}_global_unique", table, [col], unique=True)
    for table in reversed(TABLES):
        op.drop_constraint(f"fk_{table}_tenant_id_tenants", table, type_="foreignkey")
        op.drop_index(f"ix_{table}_tenant_id", table_name=table)
        op.drop_column(table, "tenant_id")
