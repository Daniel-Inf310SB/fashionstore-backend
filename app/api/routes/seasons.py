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

from app.dependencies.seasons import (
    require_seasons_manage,
)

from app.models.user import User

from app.schemas.season import (
    SeasonCreate,
    SeasonListResponse,
    SeasonResponse,
    SeasonUpdate,
)

from app.services.season_service import (
    SeasonService,
)


router = APIRouter(
    prefix="/seasons",
    tags=["Seasons"],
)


@router.get(
    "",
    response_model=SeasonListResponse,
)
def get_seasons(
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
    start_date: date | None = Query(
        default=None,
    ),
    end_date: date | None = Query(
        default=None,
    ),
    sort_by: Literal[
        "id",
        "name",
        "start_date",
        "end_date",
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
        require_seasons_manage
    ),
):

    return SeasonService.get_seasons(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
        sort_order=sort_order,
    )


@router.post(
    "",
    response_model=SeasonResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_season(
    payload: SeasonCreate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_seasons_manage
    ),
):

    try:
        return SeasonService.create_season(
            db=db,
            payload=payload,
            user_id=current_user.id,
            ip_address=(
                request.client.host
                if request.client
                else None
            ),
            user_agent=request.headers.get(
                "user-agent"
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.get(
    "/{season_id}",
    response_model=SeasonResponse,
)
def get_season(
    season_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_seasons_manage
    ),
):

    try:
        return SeasonService.get_season(
            db=db,
            season_id=season_id,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


@router.patch(
    "/{season_id}",
    response_model=SeasonResponse,
)
def update_season(
    season_id: int,
    payload: SeasonUpdate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_seasons_manage
    ),
):

    try:
        return SeasonService.update_season(
            db=db,
            season_id=season_id,
            payload=payload,
            user_id=current_user.id,
            ip_address=(
                request.client.host
                if request.client
                else None
            ),
            user_agent=request.headers.get(
                "user-agent"
            ),
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


@router.delete(
    "/{season_id}",
    response_model=SeasonResponse,
)
def deactivate_season(
    season_id: int,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_seasons_manage
    ),
):

    try:
        return SeasonService.deactivate_season(
            db=db,
            season_id=season_id,
            user_id=current_user.id,
            ip_address=(
                request.client.host
                if request.client
                else None
            ),
            user_agent=request.headers.get(
                "user-agent"
            ),
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc