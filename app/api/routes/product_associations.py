from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Request,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.dependencies.products import (
    require_products_manage,
    require_products_view,
)

from app.models.user import User

from app.schemas.product_association import (
    ProductAssociationsResponse,
    ProductCollectionCreate,
    ProductCollectionResponse,
    ProductPromotionCreate,
    ProductPromotionResponse,
    ProductSeasonCreate,
    ProductSeasonResponse,
)

from app.services.product_association_service import (
    ProductAssociationService,
)


router = APIRouter(
    prefix="/products",
    tags=["Product Associations"],
)


# =========================================================
# LISTAR TODAS
# =========================================================

@router.get(
    "/{product_id}/associations",
    response_model=
        ProductAssociationsResponse,
)
def get_product_associations(
    product_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_view
    ),
):

    try:

        return (
            ProductAssociationService
            .get_associations(
                db=db,
                product_id=product_id,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# ASOCIAR TEMPORADA
# =========================================================

@router.post(
    "/{product_id}/seasons",
    response_model=
        ProductSeasonResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def add_product_season(
    product_id: int,
    payload: ProductSeasonCreate,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    try:

        return (
            ProductAssociationService
            .add_season(
                db=db,
                product_id=product_id,
                season_id=
                    payload.season_id,
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
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# =========================================================
# QUITAR TEMPORADA
# =========================================================

@router.delete(
    "/{product_id}/seasons/{season_id}",
)
def remove_product_season(
    product_id: int,
    season_id: int,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    try:

        ProductAssociationService.remove_season(
            db=db,
            product_id=product_id,
            season_id=season_id,
            user_id=current_user.id,
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

    except LookupError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "message":
            "Temporada retirada del producto."
    }


# =========================================================
# ASOCIAR COLECCIÓN
# =========================================================

@router.post(
    "/{product_id}/collections",
    response_model=
        ProductCollectionResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def add_product_collection(
    product_id: int,
    payload:
        ProductCollectionCreate,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    try:

        return (
            ProductAssociationService
            .add_collection(
                db=db,
                product_id=product_id,
                collection_id=
                    payload.collection_id,
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
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# =========================================================
# QUITAR COLECCIÓN
# =========================================================

@router.delete(
    "/{product_id}/collections/{collection_id}",
)
def remove_product_collection(
    product_id: int,
    collection_id: int,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    try:

        ProductAssociationService.remove_collection(
            db=db,
            product_id=product_id,
            collection_id=collection_id,
            user_id=current_user.id,
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

    except LookupError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "message":
            "Colección retirada del producto."
    }


# =========================================================
# ASOCIAR PROMOCIÓN
# =========================================================

@router.post(
    "/{product_id}/promotions",
    response_model=
        ProductPromotionResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def add_product_promotion(
    product_id: int,
    payload:
        ProductPromotionCreate,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    try:

        return (
            ProductAssociationService
            .add_promotion(
                db=db,
                product_id=product_id,
                promotion_id=
                    payload.promotion_id,
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
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# =========================================================
# QUITAR PROMOCIÓN
# =========================================================

@router.delete(
    "/{product_id}/promotions/{promotion_id}",
)
def remove_product_promotion(
    product_id: int,
    promotion_id: int,
    request: Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    try:

        ProductAssociationService.remove_promotion(
            db=db,
            product_id=product_id,
            promotion_id=promotion_id,
            user_id=current_user.id,
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

    except LookupError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    return {
        "message":
            "Promoción retirada del producto."
    }