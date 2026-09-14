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

from app.dependencies.colors import (
    require_colors_manage,
)

from app.models.user import User

from app.schemas.color import (
    ColorCreate,
    ColorListResponse,
    ColorResponse,
    ColorUpdate,
)

from app.services.color_service import (
    ColorService,
)


router = APIRouter(
    prefix="/colors",
    tags=["Colors"],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        ColorListResponse,
)
def get_colors(
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
        "hex_code",
        "is_active",
        "created_at",
        "updated_at",
    ] = Query(
        default="name",
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
        require_colors_manage
    ),
):

    return (
        ColorService
        .get_colors(
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
        ColorResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def create_color(
    payload: ColorCreate,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_colors_manage
    ),
):

    try:

        return (
            ColorService
            .create_color(
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

            detail=
                str(exc),
        ) from exc


# =========================================================
# OBTENER
# =========================================================

@router.get(
    "/{color_id}",
    response_model=
        ColorResponse,
)
def get_color(
    color_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_colors_manage
    ),
):

    try:

        return (
            ColorService
            .get_color(
                db=db,

                color_id=
                    color_id,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail=
                str(exc),
        ) from exc


# =========================================================
# ACTUALIZAR
# =========================================================

@router.patch(
    "/{color_id}",
    response_model=
        ColorResponse,
)
def update_color(
    color_id: int,

    payload: ColorUpdate,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_colors_manage
    ),
):

    try:

        return (
            ColorService
            .update_color(
                db=db,

                color_id=
                    color_id,

                payload=
                    payload,

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

            detail=
                str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                str(exc),
        ) from exc


# =========================================================
# DESACTIVAR
# =========================================================

@router.delete(
    "/{color_id}",
    response_model=
        ColorResponse,
)
def deactivate_color(
    color_id: int,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_colors_manage
    ),
):

    try:

        return (
            ColorService
            .deactivate_color(
                db=db,

                color_id=
                    color_id,

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

            detail=
                str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,

            detail=
                str(exc),
        ) from exc