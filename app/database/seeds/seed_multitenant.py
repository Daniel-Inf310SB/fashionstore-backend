"""Orquestador por bloques: sin borrar tablas ni invocar seeds obsoletos."""
import argparse
from sqlalchemy import text
from app.database.seeds.seed_demo_config import DEMO_TENANTS, EXPECTED_DATABASE, EXPECTED_ALEMBIC_HEAD

def main():
    parser = argparse.ArgumentParser(description="Seeds FashionStore por bloques")
    parser.add_argument("--plan", action="store_true")
    parser.add_argument("--stage", choices=["tenants", "staff", "saas", "catalog", "inventory", "commerce", "campaigns"])
    parser.add_argument("--confirm", action="store_true")
    args = parser.parse_args()
    if args.plan:
        for p in DEMO_TENANTS:
            print(f"{p.name}: {p.branches} sucursales, {p.branches * (p.managers_per_branch + p.cashiers_per_branch)} empleados")
        return
    if not args.stage or not args.confirm:
        parser.error("Usa --stage tenants|staff|saas|catalog|inventory|commerce|campaigns --confirm")
    from app.database.session import SessionLocal
    import app.models  # Registro completo de todos los mappers
    from sqlalchemy.orm import configure_mappers
    from app.database.seeds.seed_tenants import seed_tenants
    with SessionLocal() as db:
        actual = db.scalar(text("SELECT current_database()"))
        if actual != EXPECTED_DATABASE:
            raise RuntimeError(f"Base no permitida: {actual}")
        heads = db.execute(text("SELECT version_num FROM alembic_version")).scalars().all()
        if heads != [EXPECTED_ALEMBIC_HEAD]:
            raise RuntimeError(f"Revisión inesperada: {heads}")
        configure_mappers()
        try:
            tenant_ids = seed_tenants(db)
            db.flush()
            if args.stage == "saas":
                from app.database.seeds.seed_saas_plans import seed as seed_saas
                seed_saas(db)
                print("Planes y suscripciones SaaS preparados")
            if args.stage == "catalog":
                from app.database.seeds.seed_catalog import seed_catalog
                from app.database.seeds.seed_suppliers import seed_suppliers
                # Bloques 1 y 2 deben existir primero.
                from app.models.branch import Branch
                from sqlalchemy import select, func
                for spec in DEMO_TENANTS:
                    existing = db.scalar(select(func.count(Branch.id)).where(Branch.tenant_id == tenant_ids[spec.slug]))
                    if existing != spec.branches:
                        raise RuntimeError(f"Completa Bloque 2: {spec.slug} tiene {existing}/{spec.branches} sucursales")
                catalog = seed_catalog(db, tenant_ids)
                summary = seed_suppliers(db, tenant_ids, catalog)
                print("Bloque 3 preparado:", summary)
            if args.stage == "inventory":
                from app.database.seeds.seed_inventory import seed_inventory_multitenant
                report = seed_inventory_multitenant(db, tenant_ids)
                print("Bloque 4 preparado:", report)
            if args.stage == "commerce":
                from app.database.seeds.seed_commerce import seed_commerce
                result = seed_commerce(db, tenant_ids)
                print("Bloque 5 preparado:", result)
            if args.stage == "campaigns":
                from app.database.seeds.seed_campaigns import seed_campaigns
                summary = seed_campaigns(db, tenant_ids)
                print("Campañas y notificaciones DEMO:", summary)
            if args.stage == "staff":
                from app.database.seeds.seed_auth import seed_auth
                from app.database.seeds.seed_locations import seed_locations
                from app.database.seeds.seed_users import seed_users
                from app.database.seeds.seed_staffing import seed_staffing
                roles = seed_auth(db)
                branches = seed_locations(db, tenant_ids)
                people = seed_users(db, tenant_ids, roles, branches)
                inserted = seed_staffing(db, branches, people)
                print(f"Bloque 2 preparado: {len(branches)} sucursales, {sum(map(len, people.values()))} empleados; {inserted} asignaciones nuevas")
            db.commit()
            print("Bloque confirmado. Tenants:", tenant_ids)
        except Exception:
            db.rollback()
            raise

if __name__ == "__main__":
    main()
