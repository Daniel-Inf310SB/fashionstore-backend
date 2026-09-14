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

from app.dependencies.global_inventory import (
    require_global_inventory_view,
)

from app.models.user import (
    User,
)

from app.schemas.global_inventory import (
    GlobalInventoryListResponse,
)

from app.services.global_inventory import (
    GlobalInventoryService,
)


router = APIRouter(
    prefix="/global-inventory",

    tags=[
        "Global Inventory"
    ],
)


# =========================================================
# CONSULTAR INVENTARIO GLOBAL
# =========================================================

@router.get(
    "",

    response_model=
        GlobalInventoryListResponse,
)
def get_global_inventory(
    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=20,
        ge=1,
        le=100,
    ),

    search: str | None = Query(
        default=None,
    ),

    branch_id: int | None = Query(
        default=None,
        ge=1,
    ),

    product_id: int | None = Query(
        default=None,
        ge=1,
    ),

    product_variant_id: int | None = Query(
        default=None,
        ge=1,
    ),

    is_active: bool | None = Query(
        default=True,
    ),

    low_stock: bool | None = Query(
        default=None,
    ),

    out_of_stock: bool | None = Query(
        default=None,
    ),

    sort_by: Literal[
        "product_variant_id",
        "branch_count",
        "total_stock",
        "total_reserved",
        "total_available",
        "low_stock_branches",
        "out_of_stock_branches",
        "last_updated_at",
    ] = Query(
        default="total_available",
    ),

    sort_order: Literal[
        "asc",
        "desc",
    ] = Query(
        default="desc",
    ),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_global_inventory_view
    ),
):

    return (
        GlobalInventoryService
        .get_global_inventory(
            db=db,

            page=page,

            page_size=page_size,

            search=search,

            branch_id=
                branch_id,

            product_id=
                product_id,

            product_variant_id=
                product_variant_id,

            is_active=
                is_active,

            low_stock=
                low_stock,

            out_of_stock=
                out_of_stock,

            sort_by=
                sort_by,

            sort_order=
                sort_order,
        )
    )