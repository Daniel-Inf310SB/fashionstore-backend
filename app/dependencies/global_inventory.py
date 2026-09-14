from fastapi import (
    Depends,
)

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import User


# =========================================================
# CONSULTAR INVENTARIO GLOBAL
# =========================================================

def require_global_inventory_view(
    current_user: User = Depends(
        require_permission(
            "inventory.view"
        )
    ),
) -> User:

    return current_user