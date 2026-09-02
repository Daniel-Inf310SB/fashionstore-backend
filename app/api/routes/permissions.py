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

from app.schemas.permission import (
    PermissionCreate,
    PermissionListResponse,
    PermissionResponse,
    PermissionUpdate,
)

from app.services.permission_service import (
    PermissionService,
)


router = APIRouter(
    prefix="/permissions",
    tags=["Permissions"],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        PermissionListResponse,
)
def list_permissions(
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
        default="code",
        pattern=(
            r"^(id|code|name|created_at|updated_at)$"
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
        PermissionService
        .list_permissions(
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
    "/{permission_id}",
    response_model=
        PermissionResponse,
)
def get_permission(
    permission_id: int,

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
            PermissionService
            .get_permission(
                db=db,

                permission_id=
                    permission_id,
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
        PermissionResponse,

    status_code=
        status.HTTP_201_CREATED,
)
def create_permission(
    data: PermissionCreate,

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
            PermissionService
            .create_permission(
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
    "/{permission_id}",
    response_model=
        PermissionResponse,
)
def update_permission(
    permission_id: int,

    data: PermissionUpdate,

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
            PermissionService
            .update_permission(
                db=db,

                permission_id=
                    permission_id,

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
# DESACTIVAR
# =========================================================

@router.delete(
    "/{permission_id}",
    status_code=
        status.HTTP_204_NO_CONTENT,
)
def delete_permission(
    permission_id: int,

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

        PermissionService.delete_permission(
            db=db,

            permission_id=
                permission_id,

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