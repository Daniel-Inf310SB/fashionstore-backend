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

from app.dependencies.supplier_products import (
    require_supplier_products_manage,
)

from app.models.user import User

from app.schemas.supplier_product import (
    SupplierProductCreate,
    SupplierProductListResponse,
    SupplierProductResponse,
    SupplierProductUpdate,
)

from app.services.supplier_products import (
    SupplierProductService,
)


router = APIRouter(
    prefix="/supplier-products",
    tags=[
        "Supplier Products"
    ],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        SupplierProductListResponse,
)
def get_supplier_products(
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
    supplier_id: int | None = Query(
        default=None,
        ge=1,
    ),
    product_id: int | None = Query(
        default=None,
        ge=1,
    ),
    is_active: bool | None = Query(
        default=None,
    ),
    sort_by: Literal[
        "id",
        "supplier_id",
        "product_id",
        "supplier_code",
        "purchase_price",
        "minimum_order_quantity",
        "lead_time_days",
        "is_active",
        "created_at",
        "updated_at",
    ] = Query(
        default="created_at",
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
        require_supplier_products_manage
    ),
):

    return (
        SupplierProductService
        .get_supplier_products(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            supplier_id=supplier_id,
            product_id=product_id,
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
        SupplierProductResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def create_supplier_product(
    payload: SupplierProductCreate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_supplier_products_manage
    ),
):

    try:

        return (
            SupplierProductService
            .create_supplier_product(
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
# OBTENER
# =========================================================

@router.get(
    "/{supplier_product_id}",
    response_model=
        SupplierProductResponse,
)
def get_supplier_product(
    supplier_product_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_supplier_products_manage
    ),
):

    try:

        return (
            SupplierProductService
            .get_supplier_product(
                db=db,
                supplier_product_id=
                    supplier_product_id,
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
    "/{supplier_product_id}",
    response_model=
        SupplierProductResponse,
)
def update_supplier_product(
    supplier_product_id: int,
    payload: SupplierProductUpdate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_supplier_products_manage
    ),
):

    try:

        return (
            SupplierProductService
            .update_supplier_product(
                db=db,
                supplier_product_id=
                    supplier_product_id,
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
    "/{supplier_product_id}",
    response_model=
        SupplierProductResponse,
)
def deactivate_supplier_product(
    supplier_product_id: int,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_supplier_products_manage
    ),
):

    try:

        return (
            SupplierProductService
            .deactivate_supplier_product(
                db=db,
                supplier_product_id=
                    supplier_product_id,
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