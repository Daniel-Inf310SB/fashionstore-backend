from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)

from sqlalchemy.exc import (
    IntegrityError,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.dependencies.users import (
    require_users_manage,
)

from app.models.user import User

from app.schemas.user import (
    UserCreate,
    UserListResponse,
    UserResponse,
    UserUpdate,
)

from app.services.user_service import (
    UserService,
)


router = APIRouter(
    prefix="/users",
    tags=["Users"],
)


# =========================================================
# LISTAR USUARIOS
# =========================================================

@router.get(
    "",
    response_model=
        UserListResponse,
)
def list_users(
    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
    ),

    search: str | None = Query(
        default=None,
        max_length=100,
    ),

    role_id: int | None = Query(
        default=None,
        ge=1,
    ),

    is_active: bool | None = Query(
        default=None,
    ),

    is_verified: bool | None = Query(
        default=None,
    ),

    profile_completed: bool | None = Query(
        default=None,
    ),

    sort_by: str = Query(
        default="created_at",
        pattern=(
            r"^(id|username|first_name|email|"
            r"created_at|updated_at|last_login_at)$"
        ),
    ),

    sort_order: str = Query(
        default="desc",
        pattern=r"^(asc|desc)$",
    ),

    db: Session = Depends(
        get_db
    ),

    _: User = Depends(
        require_users_manage
    ),
):

    return (
        UserService
        .list_users(
            db=db,

            page=page,

            page_size=
                page_size,

            search=
                search,

            role_id=
                role_id,

            is_active=
                is_active,

            is_verified=
                is_verified,

            profile_completed=
                profile_completed,

            sort_by=
                sort_by,

            sort_order=
                sort_order,
        )
    )


# =========================================================
# OBTENER USUARIO
# =========================================================

@router.get(
    "/{user_id}",
    response_model=
        UserResponse,
)
def get_user(
    user_id: int,

    db: Session = Depends(
        get_db
    ),

    _: User = Depends(
        require_users_manage
    ),
):

    try:

        return (
            UserService
            .get_user(
                db=db,

                user_id=
                    user_id,
            )
        )

    except LookupError as error:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail=
                str(error),
        )


# =========================================================
# CREAR USUARIO
# =========================================================

@router.post(
    "",
    response_model=
        UserResponse,

    status_code=
        status.HTTP_201_CREATED,
)
def create_user(
    data: UserCreate,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_users_manage
    ),
):

    try:

        return (
            UserService
            .create_user(
                db=db,

                data=data,

                current_user_id=
                    current_user.id,

                ip_address=(
                    request.client.host
                    if request.client
                    else None
                ),

                user_agent=
                    request.headers.get(
                        "user-agent"
                    ),
            )
        )

    except ValueError as error:

        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail=
                str(error),
        )

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail=(
                "No se pudo crear el usuario. "
                "Verifica correo, usuario "
                "y número de documento."
            ),
        )


# =========================================================
# ACTUALIZAR USUARIO
# =========================================================

@router.patch(
    "/{user_id}",
    response_model=
        UserResponse,
)
def update_user(
    user_id: int,

    data: UserUpdate,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_users_manage
    ),
):

    try:

        return (
            UserService
            .update_user(
                db=db,

                user_id=
                    user_id,

                data=data,

                current_user_id=
                    current_user.id,

                ip_address=(
                    request.client.host
                    if request.client
                    else None
                ),

                user_agent=
                    request.headers.get(
                        "user-agent"
                    ),
            )
        )

    except LookupError as error:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail=
                str(error),
        )

    except ValueError as error:

        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail=
                str(error),
        )

    except IntegrityError:

        db.rollback()

        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail=(
                "No se pudo actualizar "
                "el usuario por un dato duplicado."
            ),
        )


# =========================================================
# DESACTIVAR USUARIO
# =========================================================

@router.delete(
    "/{user_id}",
    status_code=
        status.HTTP_204_NO_CONTENT,
)
def delete_user(
    user_id: int,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_users_manage
    ),
):

    try:

        UserService.delete_user(
            db=db,

            user_id=
                user_id,

            current_user_id=
                current_user.id,

            ip_address=(
                request.client.host
                if request.client
                else None
            ),

            user_agent=
                request.headers.get(
                    "user-agent"
                ),
        )

    except LookupError as error:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail=
                str(error),
        )

    except ValueError as error:

        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail=
                str(error),
        )

    return Response(
        status_code=
            status.HTTP_204_NO_CONTENT
    )