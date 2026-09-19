from fastapi import Depends

from app.dependencies.permissions import require_permission
from app.models.user import User


def require_ai_recommendations(
    current_user: User = Depends(
        require_permission("ai.recommendations")
    ),
) -> User:
    return current_user


def require_ai_assistant(
    current_user: User = Depends(
        require_permission("ai.assistant")
    ),
) -> User:
    return current_user


def require_ai_reports(
    current_user: User = Depends(
        require_permission("ai.reports")
    ),
) -> User:
    return current_user


def require_virtual_fitting(
    current_user: User = Depends(
        require_permission("virtual_fitting.use")
    ),
) -> User:
    return current_user
