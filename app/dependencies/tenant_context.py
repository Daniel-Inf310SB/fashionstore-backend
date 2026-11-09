"""Dependencias para operaciones de empresa y administración global."""
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.permissions import require_authenticated_user
from app.models.user import User
from app.services.auth_service import AuthService


def require_tenant_user(
    user: User = Depends(require_authenticated_user),
    db: Session = Depends(get_db),
) -> User:
    AuthService.validate_tenant_access(db, user)
    if user.tenant_id is None or (
        user.platform_admin is not None and user.platform_admin.is_active
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Se requiere una cuenta empresarial")
    return user


def require_platform_admin(
    user: User = Depends(require_authenticated_user),
) -> User:
    if (
        not user.is_active
        or user.tenant_id is not None
        or user.role is None
        or user.role.name != "SUPER_ADMIN"
        or user.platform_admin is None
        or not user.platform_admin.is_active
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail="Se requiere SUPER_ADMIN activo")
    return user
