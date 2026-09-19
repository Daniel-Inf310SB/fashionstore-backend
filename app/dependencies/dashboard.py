from __future__ import annotations

from fastapi import Depends

from app.dependencies.permissions import require_permission
from app.models.user import User


require_dashboard_view = require_permission("dashboard.view")


def get_dashboard_user(
    current_user: User = Depends(require_dashboard_view),
) -> User:
    return current_user
