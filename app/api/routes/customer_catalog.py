from decimal import Decimal

from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    Query,
)

from sqlalchemy.orm import (
    Session,
)

from app.database.session import (
    get_db,
)

from app.schemas.customer_catalog import (
    CustomerCatalogListResponse,
)

from app.services.customer_catalog import (
    CustomerCatalogService,
)


router = APIRouter(
    prefix="/store/catalog",

    tags=[
        "Store - Customer Catalog"
    ],
)


# =========================================================
# CU24 - CONSULTAR CATÁLOGO
# CU25 - BUSCAR Y FILTRAR PRENDAS
# =========================================================

@router.get(
    "",
    response_model=
        CustomerCatalogListResponse,
)
def get_customer_catalog(

    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=12,
        ge=1,
        le=100,
    ),

    # =====================================================
    # SUCURSAL OPCIONAL
    # =====================================================

    branch_id: int | None = Query(
        default=None,
        ge=1,
    ),

    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=150,
    ),

    audience: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),

    category: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),

    size_id: int | None = Query(
        default=None,
        ge=1,
    ),

    color_id: int | None = Query(
        default=None,
        ge=1,
    ),

    min_price: Decimal | None = Query(
        default=None,
        ge=0,
    ),

    max_price: Decimal | None = Query(
        default=None,
        ge=0,
    ),

    promotion: bool | None = Query(
        default=None,
    ),

    in_stock: bool | None = Query(
        default=None,
    ),

    sort_by: Literal[
        "name",
        "price",
        "created_at",
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
):

    return (
        CustomerCatalogService
        .get_catalog(
            db=db,

            page=page,

            page_size=
                page_size,

            branch_id=
                branch_id,

            search=
                search,

            audience=
                audience,

            category=
                category,

            size_id=
                size_id,

            color_id=
                color_id,

            min_price=
                min_price,

            max_price=
                max_price,

            promotion=
                promotion,

            in_stock=
                in_stock,

            sort_by=
                sort_by,

            sort_order=
                sort_order,
        )
    )