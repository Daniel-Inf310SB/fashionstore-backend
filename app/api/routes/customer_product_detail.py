from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
)

from sqlalchemy.orm import (
    Session,
)

from app.database.session import (
    get_db,
)

from app.schemas.customer_product_detail import (
    CustomerProductAvailabilityResponse,
    CustomerProductDetailResponse,
)

from app.services.customer_product_detail import (
    CustomerProductDetailService,
)


router = APIRouter(
    prefix="/store/products",

    tags=[
        "Store - Customer Products"
    ],
)


# =========================================================
# CU26 - CONSULTAR DISPONIBILIDAD POR SUCURSAL
# =========================================================

@router.get(
    "/{product_id}/availability",

    response_model=
        CustomerProductAvailabilityResponse,
)
def get_customer_product_availability(

    product_id: int = Path(
        ...,
        ge=1,
    ),

    variant_id: int = Query(
        ...,
        ge=1,
    ),

    # =====================================================
    # CIUDAD OPCIONAL
    # =====================================================

    city_id: int | None = Query(
        default=None,
        ge=1,
    ),

    db: Session = Depends(
        get_db
    ),
):

    return (
        CustomerProductDetailService
        .get_variant_availability(
            db=db,

            product_id=
                product_id,

            variant_id=
                variant_id,

            city_id=
                city_id,
        )
    )


# =========================================================
# CU26 - CONSULTAR DETALLE DE PRENDA
# =========================================================

@router.get(
    "/{product_id}",

    response_model=
        CustomerProductDetailResponse,
)
def get_customer_product_detail(

    product_id: int = Path(
        ...,
        ge=1,
    ),

    # =====================================================
    # SUCURSAL OPCIONAL
    # =====================================================

    branch_id: int | None = Query(
        default=None,
        ge=1,
    ),

    db: Session = Depends(
        get_db
    ),
):

    return (
        CustomerProductDetailService
        .get_product_detail(
            db=db,

            product_id=
                product_id,

            branch_id=
                branch_id,
        )
    )