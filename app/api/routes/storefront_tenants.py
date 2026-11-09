"""Directorio público de empresas y resolución del contexto de tienda."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.models.tenant import Tenant

router = APIRouter(prefix="/store/tenants", tags=["Store - Public Tenants"])

@router.get("")
def public_tenants(db: Session = Depends(get_db)):
    tenants = db.query(Tenant).filter(Tenant.is_active.is_(True)).order_by(Tenant.name).all()
    return {"items": [{"id": t.id, "slug": t.slug, "name": t.name, "logo_url": t.logo_url} for t in tenants]}

@router.get("/{slug}")
def public_tenant(slug: str, db: Session = Depends(get_db)):
    tenant = db.query(Tenant).filter(Tenant.slug == slug, Tenant.is_active.is_(True)).first()
    if tenant is None:
        raise HTTPException(status_code=404, detail="Tienda no disponible")
    return {"id": tenant.id, "slug": tenant.slug, "name": tenant.name, "logo_url": tenant.logo_url}
