from fastapi import Depends

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import User


# =========================================================
# CONSULTAR PERSONAL DE SUCURSAL
# =========================================================

def require_employee_branches_view(
    current_user: User = Depends(
        require_permission(
            "branch_staff.view"
        )
    ),
) -> User:

    return current_user


# =========================================================
# GESTIONAR PERSONAL DE SUCURSAL
# =========================================================

def require_employee_branches_manage(
    current_user: User = Depends(
        require_permission(
            "branch_staff.manage"
        )
    ),
) -> User:

    return current_user
