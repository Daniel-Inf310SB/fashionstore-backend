from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status as http_status,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.dependencies.branch_stock import (
    require_branch_stock_view,
)

from app.models.user import User

from app.schemas.branch_stock import (
    BranchStockListResponse,
)

from app.services.branch_stock import (
    BranchStockService,
)


router = APIRouter(
    prefix="/branch-stock",

    tags=[
        "Branch Stock"
    ],
)


# =========================================================
# EXISTENCIAS POR SUCURSAL
# =========================================================

@router.get(
    "",

    response_model=
        BranchStockListResponse,
)
def get_branch_stock(
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

    low_stock: bool | None = Query(
        default=None,
    ),

    out_of_stock: bool | None = Query(
        default=None,
    ),

    is_active: bool | None = Query(
        default=True,
    ),

    sort_by: Literal[
        "id",
        "branch_id",
        "product_variant_id",
        "stock_quantity",
        "reserved_quantity",
        "available_quantity",
        "minimum_stock",
        "maximum_stock",
        "reorder_point",
        "updated_at",
    ] = Query(
        default="updated_at",
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
        require_branch_stock_view
    ),
):

    try:

        return (
            BranchStockService
            .get_branch_stock(
                db=db,

                current_user=
                    current_user,

            page=page,

            page_size=page_size,

            search=search,

            branch_id=
                branch_id,

            product_id=
                product_id,

            product_variant_id=
                product_variant_id,

            low_stock=
                low_stock,

            out_of_stock=
                out_of_stock,

            is_active=
                is_active,

            sort_by=
                sort_by,

                sort_order=
                    sort_order,
            )
        )

    except PermissionError as exc:

        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except LookupError as exc:

        raise HTTPException(
            status_code=http_status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=http_status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc