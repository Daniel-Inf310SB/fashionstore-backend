from fastapi import Depends, HTTPException, status

from app.dependencies.permissions import (
    require_authenticated_user,
    require_permission,
)
from app.models.user import User


def require_sales_create(
    current_user: User = Depends(
        require_permission("sales.create")
    ),
) -> User:
    return current_user


def require_sales_view(
    current_user: User = Depends(
        require_permission("sales.view")
    ),
) -> User:
    return current_user


def require_sales_manage(
    current_user: User = Depends(
        require_permission("sales.manage")
    ),
) -> User:
    return current_user


def require_sales_cancel(
    current_user: User = Depends(
        require_authenticated_user
    ),
) -> User:
    """
    Permite entrar al endpoint de cancelación cuando el usuario puede:
    - registrar ventas (CAJERO), o
    - gestionar ventas (ENCARGADO / ADMINISTRADOR).

    La regla final de alcance (venta propia / sucursal propia / cualquier
    sucursal) se valida nuevamente en SaleService.cancel_sale().
    """

    active_permissions = {
        permission.code
        for permission in current_user.role.permissions
        if permission.is_active
    }

    if not (
        "sales.create" in active_permissions
        or "sales.manage" in active_permissions
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "No tienes permiso para cancelar ventas presenciales."
            ),
        )

    return current_user
