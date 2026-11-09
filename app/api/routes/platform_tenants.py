"""Administración global. Todas las rutas requieren SUPER_ADMIN activo."""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.database.session import get_db
from app.dependencies.tenant_context import require_platform_admin
from app.models.role import Role
from app.models.tenant import Tenant
from app.models.user import User
from app.schemas.platform import (TenantCreate, TenantUpdate, TenantStatusUpdate,
    TenantOut, TenantAdminCreate, TenantAdminOut, TenantOnboardCreate, TenantOnboardOut)

router = APIRouter(prefix="/platform/tenants", tags=["Platform - Tenants"],
                   dependencies=[Depends(require_platform_admin)])


def get_tenant_or_404(db: Session, tenant_id: int) -> Tenant:
    tenant = db.get(Tenant, tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return tenant


def commit_or_conflict(db: Session) -> None:
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Dato único ya utilizado (slug, correo o usuario)") from exc


@router.get("", response_model=list[TenantOut])
def list_tenants(db: Session = Depends(get_db)):
    return db.scalars(select(Tenant).order_by(Tenant.id)).all()


@router.post("", response_model=TenantOut, status_code=status.HTTP_201_CREATED)
def create_tenant(payload: TenantCreate, db: Session = Depends(get_db)):
    tenant = Tenant(**payload.model_dump(), is_active=True)
    db.add(tenant)
    commit_or_conflict(db)
    db.refresh(tenant)
    return tenant


@router.post("/onboard", response_model=TenantOnboardOut, status_code=status.HTTP_201_CREATED)
def onboard_tenant(payload: TenantOnboardCreate, db: Session = Depends(get_db)):
    """CU52: empresa y administrador se crean en una sola transacción."""
    role = db.scalar(select(Role).where(Role.name == "TENANT_ADMIN", Role.is_active.is_(True)))
    if role is None:
        raise HTTPException(status_code=409, detail="Rol TENANT_ADMIN no disponible")
    if db.scalar(select(User.id).where(User.email == payload.admin.email)) is not None:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")
    if payload.admin.username and db.scalar(select(User.id).where(User.username == payload.admin.username)) is not None:
        raise HTTPException(status_code=409, detail="Ese nombre de usuario ya está registrado")
    tenant = Tenant(**payload.tenant.model_dump(), is_active=True)
    try:
        db.add(tenant)
        db.flush()  # Obtiene el ID, sin confirmar aún la empresa
        user = User(
            first_name=payload.admin.first_name.strip(),
            last_name=payload.admin.last_name,
            email=payload.admin.email,
            username=payload.admin.username,
            password_hash=hash_password(payload.admin.password),
            tenant_id=tenant.id,
            role_id=role.id,
            is_active=True, is_verified=True, profile_completed=True,
        )
        db.add(user)
        db.flush()
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Slug, correo o usuario ya utilizado") from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(tenant)
    db.refresh(user)
    return TenantOnboardOut(tenant=tenant, admin=user)


@router.get("/{tenant_id}", response_model=TenantOut)
def get_tenant(tenant_id: int, db: Session = Depends(get_db)):
    return get_tenant_or_404(db, tenant_id)


@router.patch("/{tenant_id}", response_model=TenantOut)
def update_tenant(tenant_id: int, payload: TenantUpdate, db: Session = Depends(get_db)):
    tenant = get_tenant_or_404(db, tenant_id)
    changes = payload.model_dump(exclude_unset=True)
    if any(changes.get(field) is None for field in ("name", "slug") if field in changes):
        raise HTTPException(status_code=422, detail="Nombre y slug no pueden ser nulos")
    for field, value in changes.items():
        setattr(tenant, field, value)
    commit_or_conflict(db)
    db.refresh(tenant)
    return tenant


@router.patch("/{tenant_id}/status", response_model=TenantOut)
def update_tenant_status(tenant_id: int, payload: TenantStatusUpdate,
                         db: Session = Depends(get_db)):
    tenant = get_tenant_or_404(db, tenant_id)
    tenant.is_active = payload.is_active
    commit_or_conflict(db)
    db.refresh(tenant)
    return tenant


@router.get("/{tenant_id}/admins", response_model=list[TenantAdminOut])
def list_tenant_admins(tenant_id: int, db: Session = Depends(get_db)):
    get_tenant_or_404(db, tenant_id)
    return db.scalars(select(User).join(Role, User.role_id == Role.id).where(
        User.tenant_id == tenant_id, Role.name == "TENANT_ADMIN").order_by(User.id)).all()


@router.post("/{tenant_id}/admins", response_model=TenantAdminOut,
             status_code=status.HTTP_201_CREATED)
def create_tenant_admin(tenant_id: int, payload: TenantAdminCreate,
                        db: Session = Depends(get_db)):
    tenant = get_tenant_or_404(db, tenant_id)
    if not tenant.is_active:
        raise HTTPException(status_code=409, detail="No se puede asignar un administrador a una empresa inactiva")
    role = db.scalar(select(Role).where(Role.name == "TENANT_ADMIN", Role.is_active.is_(True)))
    if role is None:
        raise HTTPException(status_code=409, detail="Rol TENANT_ADMIN no disponible; revisar seeds")
    if db.scalar(select(User.id).where(User.email == payload.email)) is not None:
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo. Utiliza un correo único para el administrador")
    if payload.username and db.scalar(select(User.id).where(User.username == payload.username)) is not None:
        raise HTTPException(status_code=409, detail="Ese nombre de usuario ya está registrado")
    user = User(first_name=payload.first_name.strip(), last_name=payload.last_name,
                email=payload.email, username=payload.username,
                password_hash=hash_password(payload.password), tenant_id=tenant.id,
                role_id=role.id, is_active=True, is_verified=True,
                profile_completed=True)
    db.add(user)
    commit_or_conflict(db)
    db.refresh(user)
    return user
