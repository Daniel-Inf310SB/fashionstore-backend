from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.dependencies.sizes import (
    require_sizes_manage,
)

from app.models.user import User

from app.schemas.size import (
    SizeCreate,
    SizeListResponse,
    SizeResponse,
    SizeUpdate,
)

from app.services.size_service import (
    SizeService,
)


router = APIRouter(
    prefix="/sizes",
    tags=["Sizes"],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        SizeListResponse,
)
def get_sizes(
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
    ),
    is_active: bool | None = Query(
        default=None,
    ),
    sort_by: Literal[
        "id",
        "name",
        "sort_order",
        "is_active",
        "created_at",
        "updated_at",
    ] = Query(
        default="sort_order",
    ),
    sort_order: Literal[
        "asc",
        "desc",
    ] = Query(
        default="asc",
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_sizes_manage
    ),
):

    return (
        SizeService
        .get_sizes(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )


# =========================================================
# CREAR
# =========================================================

@router.post(
    "",
    response_model=
        SizeResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def create_size(
    payload: SizeCreate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_sizes_manage
    ),
):

    try:

        return (
            SizeService
            .create_size(
                db=db,
                payload=payload,
                user_id=
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

    except ValueError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# OBTENER
# =========================================================

@router.get(
    "/{size_id}",
    response_model=
        SizeResponse,
)
def get_size(
    size_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_sizes_manage
    ),
):

    try:

        return (
            SizeService
            .get_size(
                db=db,
                size_id=size_id,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# ACTUALIZAR
# =========================================================

@router.patch(
    "/{size_id}",
    response_model=
        SizeResponse,
)
def update_size(
    size_id: int,
    payload: SizeUpdate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_sizes_manage
    ),
):

    try:

        return (
            SizeService
            .update_size(
                db=db,
                size_id=size_id,
                payload=payload,
                user_id=
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

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# DESACTIVAR
# =========================================================

@router.delete(
    "/{size_id}",
    response_model=
        SizeResponse,
)
def deactivate_size(
    size_id: int,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_sizes_manage
    ),
):

    try:

        return (
            SizeService
            .deactivate_size(
                db=db,
                size_id=size_id,
                user_id=
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

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc