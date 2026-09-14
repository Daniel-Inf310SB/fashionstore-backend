from fastapi import Depends

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import User


# =========================================================
# GESTIONAR INVENTARIO
# =========================================================

def require_inventory_manage(
    current_user: User = Depends(
        require_permission(
            "inventory.manage"
        )
    ),
) -> User:

    return current_user