from datetime import date
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

from app.database.session import get_db

from app.dependencies.collections import (
    require_collections_manage,
)

from app.models.user import User

from app.schemas.collection import (
    CollectionCreate,
    CollectionListResponse,
    CollectionResponse,
    CollectionUpdate,
)

from app.services.collection_service import (
    CollectionService,
)


router = APIRouter(
    prefix="/collections",
    tags=["Collections"],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        CollectionListResponse,
)
def get_collections(
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

    launch_date_from: date | None = Query(
        default=None,
    ),

    launch_date_to: date | None = Query(
        default=None,
    ),

    sort_by: Literal[
        "id",
        "name",
        "launch_date",
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
        require_collections_manage
    ),
):

    return (
        CollectionService
        .get_collections(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            is_active=is_active,
            launch_date_from=
                launch_date_from,
            launch_date_to=
                launch_date_to,
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
        CollectionResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def create_collection(
    payload: CollectionCreate,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_collections_manage
    ),
):

    try:

        return (
            CollectionService
            .create_collection(
                db=db,

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
    "/{collection_id}",
    response_model=
        CollectionResponse,
)
def get_collection(
    collection_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_collections_manage
    ),
):

    try:

        return (
            CollectionService
            .get_collection(
                db=db,

                collection_id=
                    collection_id,
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
    "/{collection_id}",
    response_model=
        CollectionResponse,
)
def update_collection(
    collection_id: int,

    payload:
        CollectionUpdate,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_collections_manage
    ),
):

    try:

        return (
            CollectionService
            .update_collection(
                db=db,

                collection_id=
                    collection_id,

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
    "/{collection_id}",
    response_model=
        CollectionResponse,
)
def deactivate_collection(
    collection_id: int,

    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_collections_manage
    ),
):

    try:

        return (
            CollectionService
            .deactivate_collection(
                db=db,

                collection_id=
                    collection_id,

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