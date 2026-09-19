from fastapi import Depends

from app.dependencies.permissions import require_permission
from app.models.user import User


def require_purchases_create(
    current_user: User = Depends(require_permission("purchases.create")),
) -> User:
    return current_user


def require_purchases_view(
    current_user: User = Depends(require_permission("purchases.view")),
) -> User:
    return current_user


def require_purchases_manage(
    current_user: User = Depends(require_permission("purchases.manage")),
) -> User:
    return current_user
