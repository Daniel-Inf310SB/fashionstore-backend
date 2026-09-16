from fastapi import Depends, HTTPException, status

from app.dependencies.permissions import require_permission
from app.models.user import User


# =========================================================
# HELPERS
# =========================================================

def _require_admin(current_user: User) -> User:
    role_name = (
        current_user.role.name
        if current_user.role is not None
        else None
    )

    if role_name != "ADMINISTRADOR":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Esta operación de pagos está reservada al administrador.",
        )

    return current_user


# =========================================================
# CU39 - CONSULTAR PAGOS / ESTADO
# =========================================================

def require_payments_view(
    current_user: User = Depends(
        require_permission("payments.view")
    ),
) -> User:
    return _require_admin(current_user)


# =========================================================
# CU38 - GESTIONAR PAGOS
# =========================================================

def require_payments_manage(
    current_user: User = Depends(
        require_permission("payments.manage")
    ),
) -> User:
    return _require_admin(current_user)
