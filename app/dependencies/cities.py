from fastapi import Depends

from app.dependencies.permissions import require_permission
from app.models.user import User


def require_cities_manage(
    current_user: User = Depends(
        require_permission("branches.manage")
    ),
) -> User:
    return current_user