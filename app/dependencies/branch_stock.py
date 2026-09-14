from fastapi import Depends

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import User


# =========================================================
# CONSULTAR EXISTENCIAS POR SUCURSAL
# =========================================================

def require_branch_stock_view(
    current_user: User = Depends(
        require_permission(
            "inventory.view"
        )
    ),
) -> User:

    return current_user