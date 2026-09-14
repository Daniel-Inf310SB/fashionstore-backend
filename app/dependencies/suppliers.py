from fastapi import Depends

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import User


# =========================================================
# GESTIONAR PROVEEDORES
# =========================================================

def require_suppliers_manage(
    current_user: User = Depends(
        require_permission(
            "suppliers.manage"
        )
    ),
) -> User:

    return current_user
