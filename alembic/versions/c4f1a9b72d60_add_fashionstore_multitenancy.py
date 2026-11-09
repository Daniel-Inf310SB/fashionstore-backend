"""Introduce tenants and platform admins, migrate existing single-store data.

Revision ID: c4f1a9b72d60
Revises: 8a7c9e1f4b22

The existing FashionStore installation is assumed to be one company.
No SUPER_ADMIN accounts are created in this migration.
"""

from alembic import op
import sqlalchemy as sa

revision = "c4f1a9b72d60"
down_revision = "8a7c9e1f4b22"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "tenants",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("legal_name", sa.String(length=200), nullable=True),
        sa.Column("tax_id", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("phone", sa.String(length=30), nullable=True),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_tenants_id", "tenants", ["id"])
    op.create_index("ix_tenants_slug", "tenants", ["slug"], unique=True)

    op.add_column("users", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index("ix_users_tenant_id", "users", ["tenant_id"])
    op.create_foreign_key(
        "fk_users_tenant_id_tenants", "users", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT"
    )

    op.add_column("branches", sa.Column("tenant_id", sa.Integer(), nullable=True))
    op.create_index("ix_branches_tenant_id", "branches", ["tenant_id"])
    op.create_foreign_key(
        "fk_branches_tenant_id_tenants", "branches", "tenants", ["tenant_id"], ["id"], ondelete="RESTRICT"
    )

    op.create_table(
        "platform_admins",
        sa.Column("id", sa.Integer(), primary_key=True, nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", name="uq_platform_admin_user"),
    )
    op.create_index("ix_platform_admins_id", "platform_admins", ["id"])
    op.create_index("ix_platform_admins_user_id", "platform_admins", ["user_id"])

    # Backfill: existing installation represents one company.
    # Do NOT grant global platform permissions to existing administrators.
    connection = op.get_bind()
    initial_tenant_id = connection.execute(
        sa.text("""
            INSERT INTO tenants (name, slug, is_active)
            VALUES (:name, :slug, TRUE)
            RETURNING id
        """),
        {"name": "FashionStore", "slug": "fashionstore"},
    ).scalar_one()
    connection.execute(
        sa.text("UPDATE users SET tenant_id = :tenant_id WHERE tenant_id IS NULL"),
        {"tenant_id": initial_tenant_id},
    )
    connection.execute(
        sa.text("UPDATE branches SET tenant_id = :tenant_id WHERE tenant_id IS NULL"),
        {"tenant_id": initial_tenant_id},
    )


def downgrade() -> None:
    # WARNING: Downgrading removes tenant assignments and global admin records.
    # Use only with an approved backup and rollback plan.
    op.drop_index("ix_platform_admins_user_id", table_name="platform_admins")
    op.drop_index("ix_platform_admins_id", table_name="platform_admins")
    op.drop_table("platform_admins")

    op.drop_constraint("fk_branches_tenant_id_tenants", "branches", type_="foreignkey")
    op.drop_index("ix_branches_tenant_id", table_name="branches")
    op.drop_column("branches", "tenant_id")

    op.drop_constraint("fk_users_tenant_id_tenants", "users", type_="foreignkey")
    op.drop_index("ix_users_tenant_id", table_name="users")
    op.drop_column("users", "tenant_id")

    op.drop_index("ix_tenants_slug", table_name="tenants")
    op.drop_index("ix_tenants_id", table_name="tenants")
    op.drop_table("tenants")
