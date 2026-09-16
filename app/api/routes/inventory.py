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

from app.dependencies.inventory import (
    require_inventory_manage,
)

from app.models.user import User

from app.schemas.inventory import (
    InventoryCreate,
    InventoryListResponse,
    InventoryResponse,
    InventoryUpdate,
)

from app.services.inventory import (
    InventoryService,
)


router = APIRouter(
    prefix="/inventory",

    tags=[
        "Inventory"
    ],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",

    response_model=
        InventoryListResponse,
)
def get_inventories(
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

    is_active: bool | None = Query(
        default=None,
    ),

    low_stock: bool | None = Query(
        default=None,
    ),

    sort_by: Literal[
        "id",
        "branch_id",
        "product_variant_id",
        "stock_quantity",
        "reserved_quantity",
        "minimum_stock",
        "maximum_stock",
        "reorder_point",
        "is_active",
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
        require_inventory_manage
    ),
):

    try:

        return (
            InventoryService
            .get_inventories(
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

            is_active=
                is_active,

            low_stock=
                low_stock,

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


# =========================================================
# CREAR
# =========================================================

@router.post(
    "",

    response_model=
        InventoryResponse,

    status_code=
        http_status.HTTP_201_CREATED,
)
def create_inventory(
    payload:
        InventoryCreate,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_inventory_manage
    ),
):

    try:

        return (
            InventoryService
            .create_inventory(
                db=db,

                payload=
                    payload,

                current_user=
                    current_user,

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

    except PermissionError as exc:

        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

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
    "/{inventory_id}",

    response_model=
        InventoryResponse,
)
def get_inventory(
    inventory_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_inventory_manage
    ),
):

    try:

        return (
            InventoryService
            .get_inventory(
                db=db,

                inventory_id=
                    inventory_id,

                current_user=
                    current_user,
            )
        )

    except PermissionError as exc:

        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

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
    "/{inventory_id}",

    response_model=
        InventoryResponse,
)
def update_inventory(
    inventory_id: int,

    payload:
        InventoryUpdate,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_inventory_manage
    ),
):

    try:

        return (
            InventoryService
            .update_inventory(
                db=db,

                inventory_id=
                    inventory_id,

                payload=
                    payload,

                current_user=
                    current_user,

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

    except PermissionError as exc:

        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

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
# DESACTIVAR
# =========================================================

@router.delete(
    "/{inventory_id}",

    response_model=
        InventoryResponse,
)
def deactivate_inventory(
    inventory_id: int,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_inventory_manage
    ),
):

    try:

        return (
            InventoryService
            .deactivate_inventory(
                db=db,

                inventory_id=
                    inventory_id,

                current_user=
                    current_user,

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

    except PermissionError as exc:

        raise HTTPException(
            status_code=http_status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

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
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
