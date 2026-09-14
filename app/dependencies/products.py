from fastapi import Depends

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import User


# =========================================================
# VER PRODUCTOS
# =========================================================

def require_products_view(
    current_user: User = Depends(
        require_permission(
            "products.manage"
        )
    ),
) -> User:

    return current_user


# =========================================================
# GESTIONAR PRODUCTOS
# =========================================================

def require_products_manage(
    current_user: User = Depends(
        require_permission(
            "products.manage"
        )
    ),
) -> User:

    return current_user