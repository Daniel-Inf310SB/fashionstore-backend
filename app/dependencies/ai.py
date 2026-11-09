from fastapi import Depends

from app.dependencies.permissions import require_permission
from app.dependencies.plan_features import require_plan_feature
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
    current_user: User = Depends(require_permission("ai.reports")),
    _: User = Depends(require_plan_feature("ai_reports")),
) -> User:
    return current_user


def require_virtual_fitting(
    current_user: User = Depends(
        require_permission("virtual_fitting.use")
    ),
) -> User:
    return current_user
