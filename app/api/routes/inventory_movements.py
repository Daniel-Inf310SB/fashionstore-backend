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

from app.dependencies.inventory_movements import (
    require_inventory_movements_manage,
    require_inventory_movements_view,
)

from app.models.user import User

from app.schemas.inventory_movement import (
    InventoryMovementCreate,
    InventoryMovementListResponse,
    InventoryMovementResponse,
    InventoryMovementType,
)

from app.services.inventory_movements import (
    InventoryMovementService,
)


router = APIRouter(
    prefix="/inventory-movements",

    tags=[
        "Inventory Movements"
    ],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",

    response_model=
        InventoryMovementListResponse,
)
def get_inventory_movements(
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

    inventory_id: int | None = Query(
        default=None,
        ge=1,
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

    supplier_id: int | None = Query(
        default=None,
        ge=1,
    ),

    user_id: int | None = Query(
        default=None,
        ge=1,
    ),

    movement_type:
        InventoryMovementType
        | None =
        Query(
            default=None,
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
        require_inventory_movements_view
    ),
):

    return (
        InventoryMovementService
        .get_movements(
            db=db,

            page=page,

            page_size=page_size,

            search=search,

            inventory_id=
                inventory_id,

            branch_id=
                branch_id,

            product_id=
                product_id,

            product_variant_id=
                product_variant_id,

            supplier_id=
                supplier_id,

            user_id=
                user_id,

            movement_type=
                movement_type,

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
        InventoryMovementResponse,

    status_code=
        http_status.HTTP_201_CREATED,
)
def create_inventory_movement(
    payload:
        InventoryMovementCreate,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_inventory_movements_manage
    ),
):

    try:

        return (
            InventoryMovementService
            .create_movement(
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
    "/{movement_id}",

    response_model=
        InventoryMovementResponse,
)
def get_inventory_movement(
    movement_id: int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_inventory_movements_view
    ),
):

    try:

        return (
            InventoryMovementService
            .get_movement(
                db=db,

                movement_id=
                    movement_id,
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