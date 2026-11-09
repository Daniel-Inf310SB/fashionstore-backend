"""Sucursales de la tienda pública, siempre limitadas a un tenant configurado."""

import os

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.tenant import Tenant
from app.schemas.branch import BranchListResponse
from app.services.branch_service import BranchService

router = APIRouter(prefix="/store/branches", tags=["Store - Branches"])


def resolve_storefront_tenant(db: Session, slug: str | None = None) -> Tenant:
    """No aceptar tenant_id del navegador: la tienda se vincula desde el servidor."""
    slug = (slug if slug is not None else os.getenv("PUBLIC_STOREFRONT_TENANT_SLUG", "fashionstore")).strip()
    if not slug:
        raise HTTPException(status_code=503, detail="La tienda pública no tiene una empresa configurada.")
    tenant = db.query(Tenant).filter(Tenant.slug == slug, Tenant.is_active.is_(True)).first()
    if tenant is None:
        raise HTTPException(status_code=503, detail="La empresa configurada para esta tienda no está disponible.")
    return tenant


@router.get("", response_model=BranchListResponse)
def get_store_branches(
    tenant_slug: str | None = Query(default=None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    tenant = resolve_storefront_tenant(db, tenant_slug)
    return BranchService.get_branches(
        db=db,
        page=1,
        page_size=100,
        search=None,
        city_id=None,
        is_active=True,
        sort_by="name",
        sort_order="asc",
        tenant_id=tenant.id,
    )
