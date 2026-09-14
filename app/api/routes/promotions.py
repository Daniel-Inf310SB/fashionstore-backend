from datetime import datetime
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

from app.dependencies.promotions import (
    require_promotions_manage,
)

from app.models.user import User

from app.schemas.promotion import (
    PromotionCreate,
    PromotionListResponse,
    PromotionResponse,
    PromotionUpdate,
)

from app.services.promotion_service import (
    PromotionService,
)


router = APIRouter(
    prefix="/promotions",
    tags=["Promotions"],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        PromotionListResponse,
)
def get_promotions(
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

    discount_type: str | None = Query(
        default=None,
    ),

    start_from: datetime | None = Query(
        default=None,
    ),

    end_to: datetime | None = Query(
        default=None,
    ),

    sort_by: Literal[
        "id",
        "name",
        "discount_type",
        "discount_value",
        "start_at",
        "end_at",
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
        require_promotions_manage
    ),
):

    return (
        PromotionService
        .get_promotions(
            db=db,

            page=page,

            page_size=
                page_size,

            search=
                search,

            is_active=
                is_active,

            discount_type=
                discount_type,

            start_from=
                start_from,

            end_to=
                end_to,

            sort_by=
                sort_by,

            sort_order=
                sort_order,
        )
    )


# =========================================================
# CREAR
# =========================================================

@router.post(
    "",
    response_model=
        PromotionResponse,

    status_code=
        status.HTTP_201_CREATED,
)
def create_promotion(
    payload:
        PromotionCreate,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_promotions_manage
    ),
):

    try:

        return (
            PromotionService
            .create_promotion(
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
    "/{promotion_id}",
    response_model=
        PromotionResponse,
)
def get_promotion(
    promotion_id:
        int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_promotions_manage
    ),
):

    try:

        return (
            PromotionService
            .get_promotion(
                db=db,

                promotion_id=
                    promotion_id,
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
    "/{promotion_id}",
    response_model=
        PromotionResponse,
)
def update_promotion(
    promotion_id:
        int,

    payload:
        PromotionUpdate,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_promotions_manage
    ),
):

    try:

        return (
            PromotionService
            .update_promotion(
                db=db,

                promotion_id=
                    promotion_id,

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
    "/{promotion_id}",
    response_model=
        PromotionResponse,
)
def deactivate_promotion(
    promotion_id:
        int,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_promotions_manage
    ),
):

    try:

        return (
            PromotionService
            .deactivate_promotion(
                db=db,

                promotion_id=
                    promotion_id,

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