from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status as http_status,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.dependencies.supplier_availability import (
    require_supplier_availability_manage,
)

from app.models.user import (
    User,
)

from app.schemas.supplier_availability import (
    SupplierAvailabilityCreate,
    SupplierAvailabilityListResponse,
    SupplierAvailabilityResponse,
    SupplierAvailabilityUpdate,
)

from app.services.supplier_availability import (
    SupplierAvailabilityService,
)


router = APIRouter(
    prefix="/supplier-availability",

    tags=[
        "Supplier Availability"
    ],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",

    response_model=
        SupplierAvailabilityListResponse,
)
def get_supplier_availabilities(
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

    supplier_product_id:
        int | None = Query(
            default=None,
            ge=1,
        ),

    product_id:
        int | None = Query(
            default=None,
            ge=1,
        ),

    product_variant_id:
        int | None = Query(
            default=None,
            ge=1,
        ),

    status: Literal[
        "AVAILABLE",
        "LOW_STOCK",
        "OUT_OF_STOCK",
    ] | None = Query(
        default=None,
    ),

    sort_by: Literal[
        "id",
        "supplier_product_id",
        "product_variant_id",
        "available_quantity",
        "status",
        "purchase_price",
        "last_checked_at",
        "created_at",
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
        require_supplier_availability_manage
    ),
):

    return (
        SupplierAvailabilityService
        .get_availabilities(
            db=db,

            page=page,

            page_size=page_size,

            search=search,

            supplier_id=
                supplier_id,

            supplier_product_id=
                supplier_product_id,

            product_id=
                product_id,

            product_variant_id=
                product_variant_id,

            status=
                status,

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
        SupplierAvailabilityResponse,

    status_code=
        http_status.HTTP_201_CREATED,
)
def create_supplier_availability(
    payload:
        SupplierAvailabilityCreate,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_supplier_availability_manage
    ),
):

    try:

        return (
            SupplierAvailabilityService
            .create_availability(
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

    except LookupError as exc:

        raise HTTPException(
            status_code=
                http_status
                .HTTP_404_NOT_FOUND,

            detail=
                str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=
                http_status
                .HTTP_400_BAD_REQUEST,

            detail=
                str(exc),
        ) from exc


# =========================================================
# OBTENER
# =========================================================

@router.get(
    "/{availability_id}",

    response_model=
        SupplierAvailabilityResponse,
)
def get_supplier_availability(
    availability_id:
        int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_supplier_availability_manage
    ),
):

    try:

        return (
            SupplierAvailabilityService
            .get_availability(
                db=db,

                availability_id=
                    availability_id,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=
                http_status
                .HTTP_404_NOT_FOUND,

            detail=
                str(exc),
        ) from exc


# =========================================================
# ACTUALIZAR
# =========================================================

@router.patch(
    "/{availability_id}",

    response_model=
        SupplierAvailabilityResponse,
)
def update_supplier_availability(
    availability_id:
        int,

    payload:
        SupplierAvailabilityUpdate,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_supplier_availability_manage
    ),
):

    try:

        return (
            SupplierAvailabilityService
            .update_availability(
                db=db,

                availability_id=
                    availability_id,

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
                http_status
                .HTTP_404_NOT_FOUND,

            detail=
                str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=
                http_status
                .HTTP_400_BAD_REQUEST,

            detail=
                str(exc),
        ) from exc


# =========================================================
# ELIMINAR
# =========================================================

@router.delete(
    "/{availability_id}",
)
def delete_supplier_availability(
    availability_id:
        int,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_supplier_availability_manage
    ),
):

    try:

        return (
            SupplierAvailabilityService
            .delete_availability(
                db=db,

                availability_id=
                    availability_id,

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
                http_status
                .HTTP_404_NOT_FOUND,

            detail=
                str(exc),
        ) from exc