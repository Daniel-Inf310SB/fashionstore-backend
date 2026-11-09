"""CRUD de campañas; únicamente usuarios de empresa con permiso de productos."""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.permissions import require_permission
from app.models.home_banner import HomeBanner
from app.models.user import User
from app.schemas.home import HomeBannerInput, HomeBannerPatch, HomeBannerOut
from app.services.store_home_service import StoreHomeService

router = APIRouter(prefix="/home-banners", tags=["Home Banners - Admin"])


def require_business_user(user: User):
    if not user.is_active or user.tenant_id is None:
        raise HTTPException(status_code=403, detail="Se requiere usuario empresarial activo.")
    return user.tenant_id


def get_owned(db: Session, tenant_id: int, banner_id: int):
    banner = db.query(HomeBanner).filter(
        HomeBanner.id == banner_id, HomeBanner.tenant_id == tenant_id
    ).first()
    if not banner:
        raise HTTPException(status_code=404, detail="Banner no encontrado.")
    return banner


def apply_payload(banner, values: dict):
    for key, value in values.items():
        setattr(banner, key, str(value) if key in ("image_url", "mobile_image_url") and value is not None else value)


def validate_dates_and_target(db, tenant_id: int, values: dict):
    from datetime import timezone
    start, end = values.get("starts_at"), values.get("ends_at")
    if start and end and end <= start:
        raise HTTPException(status_code=422, detail="Fecha final debe ser posterior a la inicial.")
    StoreHomeService.validate_destination(db, tenant_id, values["target_type"], values["target_id"])


@router.get("", response_model=list[HomeBannerOut])
def list_banners(db: Session = Depends(get_db), user: User = Depends(require_permission("products.manage"))):
    tenant_id = require_business_user(user)
    return db.query(HomeBanner).filter(HomeBanner.tenant_id == tenant_id).order_by(HomeBanner.sort_order, HomeBanner.id).all()


@router.post("", response_model=HomeBannerOut, status_code=201)
def create_banner(payload: HomeBannerInput, db: Session = Depends(get_db), user: User = Depends(require_permission("products.manage"))):
    tenant_id = require_business_user(user)
    values = payload.model_dump(mode="python")
    validate_dates_and_target(db, tenant_id, values)
    banner = HomeBanner(tenant_id=tenant_id)
    apply_payload(banner, values)
    db.add(banner)
    db.commit()
    db.refresh(banner)
    return banner


@router.patch("/{banner_id}", response_model=HomeBannerOut)
def update_banner(banner_id: int, payload: HomeBannerPatch, db: Session = Depends(get_db), user: User = Depends(require_permission("products.manage"))):
    tenant_id = require_business_user(user)
    banner = get_owned(db, tenant_id, banner_id)
    changes = payload.model_dump(exclude_unset=True)
    # Null en los campos obligatorios no está permitido.
    for key in ("title", "image_url", "target_type", "sort_order", "is_active", "show_as_popup", "popup_priority"):
        if key in changes and changes[key] is None:
            raise HTTPException(422, detail=f"{key} no puede ser null.")
    values = {key: getattr(banner, key) for key in HomeBannerInput.model_fields}
    values.update(changes)
    # Valida las mismas reglas de creación tras combinar el PATCH.
    try:
        validated = HomeBannerInput.model_validate(values)
    except Exception as exc:
        raise HTTPException(422, detail=str(exc)) from exc
    values = validated.model_dump(mode="python")
    validate_dates_and_target(db, tenant_id, values)
    apply_payload(banner, values)
    db.commit()
    db.refresh(banner)
    return banner


@router.delete("/{banner_id}", status_code=204)
def delete_banner(banner_id: int, db: Session = Depends(get_db), user: User = Depends(require_permission("products.manage"))):
    tenant_id = require_business_user(user)
    db.delete(get_owned(db, tenant_id, banner_id))
    db.commit()
