from fastapi import Depends

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import User


# =========================================================
# GESTIONAR USUARIOS
# =========================================================

def require_users_manage(
    current_user: User = Depends(
        require_permission(
            "users.manage"
        )
    ),
) -> User:

    return current_user