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
from app.dependencies.cities import require_cities_manage
from app.models.user import User
from app.schemas.city import (
    CityCreate,
    CityListResponse,
    CityResponse,
    CityUpdate,
)
from app.services.city_service import CityService


router = APIRouter(
    prefix="/cities",
    tags=["Cities"],
)


# =========================================================
# LISTAR CIUDADES
# =========================================================

@router.get(
    "",
    response_model=CityListResponse,
)
def list_cities(
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
    is_active: bool | None = Query(
        default=None,
    ),
    sort_by: Literal[
        "id",
        "name",
        "is_active",
    ] = Query(
        default="name",
    ),
    sort_order: Literal[
        "asc",
        "desc",
    ] = Query(
        default="asc",
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_cities_manage
    ),
):

    return CityService.list_cities(
        db,
        page=page,
        page_size=page_size,
        search=search,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# =========================================================
# CREAR CIUDAD
# =========================================================

@router.post(
    "",
    response_model=CityResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_city(
    payload: CityCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_cities_manage
    ),
):

    try:

        return CityService.create_city(
            db,
            payload,
            current_user_id=current_user.id,
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
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# =========================================================
# OBTENER CIUDAD
# =========================================================

@router.get(
    "/{city_id}",
    response_model=CityResponse,
)
def get_city(
    city_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_cities_manage
    ),
):

    try:

        return CityService.get_city(
            db,
            city_id,
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )


# =========================================================
# ACTUALIZAR CIUDAD
# =========================================================

@router.patch(
    "/{city_id}",
    response_model=CityResponse,
)
def update_city(
    city_id: int,
    payload: CityUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_cities_manage
    ),
):

    try:

        return CityService.update_city(
            db,
            city_id,
            payload,
            current_user_id=current_user.id,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )


# =========================================================
# DESACTIVAR CIUDAD
# =========================================================

@router.delete(
    "/{city_id}",
    response_model=CityResponse,
)
def deactivate_city(
    city_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_cities_manage
    ),
):

    try:

        return CityService.deactivate_city(
            db,
            city_id,
            current_user_id=current_user.id,
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
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )