"""Bloque 1: idempotente; no modifica ni elimina tenants preexistentes."""
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.seeds.seed_demo_config import DEMO_TENANTS
from app.models.tenant import Tenant


def seed_tenants(db: Session) -> dict[str, int]:
    ids = {}
    for spec in DEMO_TENANTS:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == spec.slug))
        if tenant is None:
            tenant = Tenant(name=spec.name, slug=spec.slug, is_active=True)
            db.add(tenant)
            db.flush()
        elif tenant.name != spec.name:
            raise RuntimeError(f'Tenant {spec.slug} ya existe con otro nombre; no se modifica')
        ids[spec.slug] = tenant.id
    return ids
