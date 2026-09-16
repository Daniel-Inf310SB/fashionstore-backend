from collections.abc import Callable

from fastapi import (
    Depends,
    HTTPException,
    status,
)

from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.user import User
from app.services.auth_service import AuthService


# =========================================================
# BEARER
# =========================================================

bearer_scheme = HTTPBearer()


# =========================================================
# REQUERIR USUARIO AUTENTICADO
#
# No exige un permiso específico.
# Valida:
# - token
# - usuario
# - rol existente
# - rol activo
#
# Se usa para endpoints de contexto personal,
# como GET /branches/my-branch.
# =========================================================

def require_authenticated_user(
    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),

    db: Session = Depends(
        get_db
    ),
) -> User:

    try:
        user = AuthService.get_user_from_access_token(
            db=db,
            access_token=credentials.credentials,
        )

    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        ) from error


    if user.role is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El usuario no tiene un rol asignado.",
        )


    if not user.role.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="El rol del usuario está desactivado.",
        )


    return user


# =========================================================
# REQUERIR PERMISO
# =========================================================

def require_permission(
    permission_code: str,
) -> Callable:

    def dependency(
        credentials: HTTPAuthorizationCredentials = Depends(
            bearer_scheme
        ),

        db: Session = Depends(
            get_db
        ),
    ) -> User:

        # =================================================
        # OBTENER USUARIO DESDE TOKEN
        # =================================================

        try:
            user = AuthService.get_user_from_access_token(
                db=db,
                access_token=credentials.credentials,
            )

        except PermissionError as error:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=str(error),
            )


        # =================================================
        # VALIDAR ROL
        # =================================================

        if user.role is None:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El usuario no tiene un rol asignado.",
            )


        if not user.role.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="El rol del usuario está desactivado.",
            )


        # =================================================
        # VALIDAR PERMISO
        # =================================================

        has_permission = any(
            permission.code == permission_code
            and permission.is_active

            for permission in user.role.permissions
        )


        if not has_permission:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=(
                    f"No tienes el permiso requerido: "
                    f"{permission_code}"
                ),
            )


        return user


    return dependency