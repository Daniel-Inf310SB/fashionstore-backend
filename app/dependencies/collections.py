from fastapi import Depends

from app.dependencies.permissions import require_permission
from app.models.user import User


def require_collections_manage(
    current_user: User = Depends(
        require_permission("products.manage")
    ),
) -> User:

    return current_user