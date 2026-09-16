from fastapi import (
    Depends,
    HTTPException,
    status,
)

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import (
    User,
)


RESERVATION_STAFF_ROLES = {
    "ADMINISTRADOR",
    "SUPERADMIN",
    "ENCARGADO_SUCURSAL",
}


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
# CU28 - CONSULTAR RESERVAS
# =========================================================

def require_reservations_view(
    current_user: User = Depends(
        require_permission(
            "reservations.view"
        )
    ),
) -> User:

    return current_user


# =========================================================
# CU28 - GESTIONAR RESERVAS
#
# Permiso general. También lo usa CLIENTE para crear o
# cancelar sus propias reservas.
# =========================================================

def require_reservations_manage(
    current_user: User = Depends(
        require_permission(
            "reservations.manage"
        )
    ),
) -> User:

    return current_user


# =========================================================
# CU28 - OPERACIONES DEL CLIENTE SOBRE SUS RESERVAS
#
# Exige el permiso del módulo y además el rol CLIENTE.
# Evita que /reservations/mine pueda convertirse en una
# vista global accidental para un administrador/encargado.
# =========================================================

def require_reservations_customer(
    current_user: User = Depends(
        require_permission(
            "reservations.manage"
        )
    ),
) -> User:

    if _role_name(current_user) != "CLIENTE":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=(
                "Esta operación corresponde al cliente "
                "sobre sus propias reservas."
            ),
        )

    return current_user


# =========================================================
# CU29 / CU30 / CU31 - GESTIÓN OPERATIVA DE RESERVAS
#
# Solo personal autorizado de tienda:
# - ADMINISTRADOR / SUPERADMIN
# - ENCARGADO_SUCURSAL
#
# El alcance por sucursal se valida nuevamente en el
# servicio para impedir acceso a reservas de otra sucursal.
# =========================================================

def require_reservations_staff_manage(
    current_user: User = Depends(
        require_permission(
            "reservations.manage"
        )
    ),
) -> User:

    if (
        _role_name(
            current_user
        )
        not in
        RESERVATION_STAFF_ROLES
    ):
        raise HTTPException(
            status_code=
                status.HTTP_403_FORBIDDEN,

            detail=(
                "La gestión operativa de reservas "
                "corresponde al administrador o al "
                "encargado de la sucursal."
            ),
        )

    return current_user
