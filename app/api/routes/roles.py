from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    Response,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.dependencies.permissions import (
    require_permission,
)

from app.models.user import User

from app.schemas.role import (
    RoleCreate,
    RoleListResponse,
    RolePermissionsUpdate,
    RoleResponse,
    RoleUpdate,
)

from app.services.role_service import (
    RoleService,
)


router = APIRouter(
    prefix="/roles",
    tags=["Roles"],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        RoleListResponse,
)
def list_roles(
    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),

    search: str | None = Query(
        default=None,
        max_length=100,
    ),

    is_active: bool | None = Query(
        default=None,
    ),

    sort_by: str = Query(
        default="name",
        pattern=(
            r"^(id|name|created_at|updated_at)$"
        ),
    ),

    sort_order: str = Query(
        default="asc",
        pattern=r"^(asc|desc)$",
    ),

    db: Session = Depends(
        get_db
    ),

    _: User = Depends(
        require_permission(
            "roles.manage"
        )
    ),
):

    return (
        RoleService
        .list_roles(
            db=db,

            page=
                page,

            page_size=
                page_size,

            search=
                search,

            is_active=
                is_active,

            sort_by=
                sort_by,

            sort_order=
                sort_order,
        )
    )


# =========================================================
# OBTENER
# =========================================================

@router.get(
    "/{role_id}",
    response_model=
        RoleResponse,
)
def get_role(
    role_id: int,

    db: Session = Depends(
        get_db
    ),

    _: User = Depends(
        require_permission(
            "roles.manage"
        )
    ),
):

    try:

        return (
            RoleService
            .get_role(
                db=db,

                role_id=
                    role_id,
            )
        )

    except ValueError as error:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail=
                str(error),
        )


# =========================================================
# CREAR
# =========================================================

@router.post(
    "",
    response_model=
        RoleResponse,

    status_code=
        status.HTTP_201_CREATED,
)
def create_role(
    data: RoleCreate,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_permission(
            "roles.manage"
        )
    ),
):

    try:

        return (
            RoleService
            .create_role(
                db=db,

                data=
                    data,

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


# =========================================================
# ACTUALIZAR
# =========================================================

@router.patch(
    "/{role_id}",
    response_model=
        RoleResponse,
)
def update_role(
    role_id: int,

    data: RoleUpdate,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_permission(
            "roles.manage"
        )
    ),
):

    try:

        return (
            RoleService
            .update_role(
                db=db,

                role_id=
                    role_id,

                data=
                    data,

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


# =========================================================
# ASIGNAR PERMISOS
# =========================================================

@router.put(
    "/{role_id}/permissions",
    response_model=
        RoleResponse,
)
def update_role_permissions(
    role_id: int,

    data: RolePermissionsUpdate,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_permission(
            "roles.manage"
        )
    ),
):

    try:

        return (
            RoleService
            .update_permissions(
                db=db,

                role_id=
                    role_id,

                permission_ids=
                    data.permission_ids,

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
                status.HTTP_400_BAD_REQUEST,

            detail=
                str(error),
        )


# =========================================================
# DESACTIVAR
# =========================================================

@router.delete(
    "/{role_id}",
    status_code=
        status.HTTP_204_NO_CONTENT,
)
def delete_role(
    role_id: int,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_permission(
            "roles.manage"
        )
    ),
):

    try:

        RoleService.delete_role(
            db=db,

            role_id=
                role_id,

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