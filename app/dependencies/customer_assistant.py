from fastapi import Depends, HTTPException, status

from app.dependencies.permissions import require_authenticated_user
from app.models.user import User


def require_customer_assistant(
    current_user: User = Depends(require_authenticated_user),
) -> User:
    role = (current_user.role.name if current_user.role else "").strip().upper()
    if role != "CLIENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El asistente de compras está disponible para usuarios con rol CLIENTE.",
        )
    return current_user
