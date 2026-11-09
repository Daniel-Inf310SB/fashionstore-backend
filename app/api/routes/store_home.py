"""Escaparate público del tenant y la sucursal seleccionada."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.api.routes.store_branches import resolve_storefront_tenant
from app.services.store_home_service import StoreHomeService
from app.schemas.home import HomeBannerOut

router = APIRouter(prefix="/store/home", tags=["Store - Home"])


@router.get("")
def get_home(
    branch_id: int = Query(..., ge=1),
    tenant_slug: str | None = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    tenant = resolve_storefront_tenant(db, tenant_slug)
    return StoreHomeService.home(db, tenant, branch_id)


@router.get("/banners", response_model=list[HomeBannerOut])
def get_home_banners(
    branch_id: int = Query(..., ge=1),
    tenant_slug: str | None = Query(None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    tenant = resolve_storefront_tenant(db, tenant_slug)
    StoreHomeService.check_branch(db, tenant.id, branch_id)
    return StoreHomeService.banners(db, tenant.id)


@router.get("/best-sellers")
def get_home_best_sellers(
    branch_id: int = Query(..., ge=1),
    tenant_slug: str | None = Query(None, min_length=1, max_length=100),
    limit: int = Query(8, ge=1, le=20),
    db: Session = Depends(get_db),
):
    tenant = resolve_storefront_tenant(db, tenant_slug)
    StoreHomeService.check_branch(db, tenant.id, branch_id)
    return {"items": StoreHomeService.best_sellers(db, tenant.id, branch_id, limit)}
