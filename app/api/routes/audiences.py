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

from app.dependencies.audiences import (
    require_audiences_manage,
)

from app.models.user import User

from app.schemas.audience import (
    AudienceCreate,
    AudienceListResponse,
    AudienceResponse,
    AudienceUpdate,
)

from app.services.audience_service import (
    AudienceService,
)


router = APIRouter(
    prefix="/audiences",
    tags=["Audiences"],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        AudienceListResponse,
)
def get_audiences(
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
        require_audiences_manage
    ),
):

    return (
        AudienceService
        .get_audiences(
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
        AudienceResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def create_audience(
    payload: AudienceCreate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_audiences_manage
    ),
):

    try:

        return (
            AudienceService
            .create_audience(
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
    "/{audience_id}",
    response_model=
        AudienceResponse,
)
def get_audience(
    audience_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_audiences_manage
    ),
):

    try:

        return (
            AudienceService
            .get_audience(
                db=db,
                audience_id=
                    audience_id,
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
    "/{audience_id}",
    response_model=
        AudienceResponse,
)
def update_audience(
    audience_id: int,
    payload: AudienceUpdate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_audiences_manage
    ),
):

    try:

        return (
            AudienceService
            .update_audience(
                db=db,
                audience_id=
                    audience_id,
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
    "/{audience_id}",
    response_model=
        AudienceResponse,
)
def deactivate_audience(
    audience_id: int,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_audiences_manage
    ),
):

    try:

        return (
            AudienceService
            .deactivate_audience(
                db=db,
                audience_id=
                    audience_id,
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