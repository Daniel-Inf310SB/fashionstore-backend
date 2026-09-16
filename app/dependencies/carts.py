from fastapi import (
    Depends,
    HTTPException,
    status,
)

from app.dependencies.permissions import (
    require_authenticated_user,
    require_permission,
)

from app.models.user import (
    User,
)


# =========================================================
# HELPERS
# =========================================================

def _role_name(
    current_user: User,
) -> str:
    if current_user.role is None:
        return ""

    return (
        current_user.role.name
        .strip()
        .upper()
    )


# =========================================================
# CU32 - ADMINISTRAR CARRITOS
#
# cart.manage también pertenece al CLIENTE para su CU32, por
# eso la vista administrativa exige además un rol de gestión.
# =========================================================

def require_carts_manage(
    current_user: User = Depends(
        require_permission(
            "cart.manage"
        )
    ),
) -> User:
    if _role_name(current_user) not in {
        "ADMINISTRADOR",
        "SUPERADMIN",
    }:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "La administración global de carritos "
                "corresponde al administrador."
            ),
        )

    return current_user


# =========================================================
# CU32 - MI CARRITO
#
# Los endpoints /carts/me son de contexto personal. Además
# de exigir autenticación, se limita el flujo al rol CLIENTE.
# El servicio vuelve a validar que cada carrito/item pertenezca
# al usuario autenticado.
# =========================================================

def require_cart_customer(
    current_user: User = Depends(
        require_authenticated_user
    ),
) -> User:
    if _role_name(current_user) != "CLIENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "El carrito de compras personal corresponde "
                "a usuarios con rol CLIENTE."
            ),
        )

    return current_user
