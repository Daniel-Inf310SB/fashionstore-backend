from fastapi import Depends

from app.dependencies.permissions import require_permission
from app.models.user import User


# =========================================================
# CU33 - REALIZAR COMPRA DIGITAL
# =========================================================

def require_purchases_create(
    current_user: User = Depends(
        require_permission("purchases.create")
    ),
) -> User:
    return current_user


# =========================================================
# CU34 - CONSULTAR HISTORIAL DE COMPRAS
# =========================================================

def require_purchases_view(
    current_user: User = Depends(
        require_permission("purchases.view")
    ),
) -> User:
    return current_user
