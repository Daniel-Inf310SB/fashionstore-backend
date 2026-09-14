from fastapi import Depends

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import User


# =========================================================
# CONSULTAR MOVIMIENTOS
# =========================================================

def require_inventory_movements_view(
    current_user: User = Depends(
        require_permission(
            "inventory.view"
        )
    ),
) -> User:

    return current_user


# =========================================================
# REGISTRAR MOVIMIENTOS
# =========================================================

def require_inventory_movements_manage(
    current_user: User = Depends(
        require_permission(
            "inventory.manage"
        )
    ),
) -> User:

    return current_user