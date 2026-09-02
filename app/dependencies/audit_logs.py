from fastapi import (
    Depends,
)

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import (
    User,
)


# =========================================================
# CONSULTAR BITÁCORA
# =========================================================

def require_audit_logs_view(
    current_user: User = Depends(
        require_permission(
            "roles.manage"
        )
    ),
) -> User:

    return current_user