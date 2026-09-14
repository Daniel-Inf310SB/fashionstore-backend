from fastapi import Depends

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import User


# =========================================================
# GESTIONAR PRODUCTOS DEL PROVEEDOR
# =========================================================

def require_supplier_products_manage(
    current_user: User = Depends(
        require_permission(
            "suppliers.manage"
        )
    ),
) -> User:

    return current_user