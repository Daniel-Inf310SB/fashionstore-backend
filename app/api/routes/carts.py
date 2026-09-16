from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Path,
    Query,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.dependencies.carts import (
    require_cart_customer,
    require_carts_manage,
)

from app.models.user import (
    User,
)

from app.schemas.cart import (
    CartActionResponse,
    CartClearResponse,
    CartCountResponse,
    CartItemAddRequest,
    CartItemQuantityUpdate,
    CartListResponse,
    CartResponse,
    MyCartResponse,
)

from app.services.cart_service import (
    CartService,
)


router = APIRouter(
    prefix="/carts",
    tags=[
        "Carts",
    ],
)


# =========================================================
# MANEJO DE ERRORES
# =========================================================

def handle_cart_error(
    error: Exception,
) -> None:
    if isinstance(
        error,
        PermissionError,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        ) from error

    if isinstance(
        error,
        LookupError,
    ):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error

    if isinstance(
        error,
        ValueError,
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        ) from error

    raise error


# =========================================================
# CU32 - CLIENTE - CONSULTAR MI CARRITO
#
# IMPORTANTE: las rutas /me van antes de /{cart_id} para que
# FastAPI no intente interpretar "me" como un entero.
# =========================================================

@router.get(
    "/me",
    response_model=MyCartResponse,
)
def get_my_cart(
    branch_id: int = Query(
        ...,
        ge=1,
    ),
    db: Session = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_cart_customer,
    ),
):
    try:
        return CartService.get_my_cart(
            db=db,
            customer_id=current_user.id,
            branch_id=branch_id,
        )
    except Exception as error:
        handle_cart_error(error)


# =========================================================
# CU32 - CLIENTE - CONTADOR PARA HEADER
# =========================================================

@router.get(
    "/me/count",
    response_model=CartCountResponse,
)
def get_my_cart_count(
    branch_id: int = Query(
        ...,
        ge=1,
    ),
    db: Session = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_cart_customer,
    ),
):
    try:
        return CartService.get_my_cart_count(
            db=db,
            customer_id=current_user.id,
            branch_id=branch_id,
        )
    except Exception as error:
        handle_cart_error(error)


# =========================================================
# CU32 - CLIENTE - AGREGAR PRODUCTO
# =========================================================

@router.post(
    "/me/items",
    response_model=CartActionResponse,
    status_code=status.HTTP_200_OK,
)
def add_item_to_my_cart(
    payload: CartItemAddRequest,
    db: Session = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_cart_customer,
    ),
):
    try:
        cart = CartService.add_item(
            db=db,
            customer_id=current_user.id,
            branch_id=payload.branch_id,
            product_variant_id=payload.product_variant_id,
            quantity=payload.quantity,
        )

        return {
            "message": "Producto agregado al carrito correctamente.",
            "cart": cart,
        }
    except Exception as error:
        handle_cart_error(error)


# =========================================================
# CU32 - CLIENTE - ACTUALIZAR CANTIDAD
# =========================================================

@router.patch(
    "/me/items/{item_id}",
    response_model=CartActionResponse,
)
def update_my_cart_item(
    payload: CartItemQuantityUpdate,
    item_id: int = Path(
        ...,
        ge=1,
    ),
    db: Session = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_cart_customer,
    ),
):
    try:
        cart = CartService.update_item_quantity(
            db=db,
            customer_id=current_user.id,
            item_id=item_id,
            quantity=payload.quantity,
        )

        return {
            "message": "Cantidad actualizada correctamente.",
            "cart": cart,
        }
    except Exception as error:
        handle_cart_error(error)


# =========================================================
# CU32 - CLIENTE - ELIMINAR PRODUCTO
# =========================================================

@router.delete(
    "/me/items/{item_id}",
    response_model=CartActionResponse,
)
def remove_my_cart_item(
    item_id: int = Path(
        ...,
        ge=1,
    ),
    db: Session = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_cart_customer,
    ),
):
    try:
        cart = CartService.remove_item(
            db=db,
            customer_id=current_user.id,
            item_id=item_id,
        )

        return {
            "message": "Producto eliminado del carrito correctamente.",
            "cart": cart,
        }
    except Exception as error:
        handle_cart_error(error)


# =========================================================
# CU32 - CLIENTE - VACIAR CARRITO
# =========================================================

@router.delete(
    "/me/items",
    response_model=CartClearResponse,
)
def clear_my_cart(
    branch_id: int = Query(
        ...,
        ge=1,
    ),
    db: Session = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_cart_customer,
    ),
):
    try:
        return CartService.clear_my_cart(
            db=db,
            customer_id=current_user.id,
            branch_id=branch_id,
        )
    except Exception as error:
        handle_cart_error(error)


# =========================================================
# CU32 - ADMIN - LISTAR / FILTRAR CARRITOS
# =========================================================

@router.get(
    "",
    response_model=CartListResponse,
)
def list_carts(
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
        max_length=100,
    ),
    cart_status: Literal[
        "ACTIVE",
        "CONVERTED",
        "ABANDONED",
    ] | None = Query(
        default=None,
        alias="status",
    ),
    branch_id: int | None = Query(
        default=None,
        ge=1,
    ),
    customer_id: int | None = Query(
        default=None,
        ge=1,
    ),
    db: Session = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_carts_manage,
    ),
):
    _ = current_user

    try:
        return CartService.list_carts(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            cart_status=cart_status,
            branch_id=branch_id,
            customer_id=customer_id,
        )
    except Exception as error:
        handle_cart_error(error)


# =========================================================
# CU32 - ADMIN - CONSULTAR DETALLE DE CARRITO
# =========================================================

@router.get(
    "/{cart_id}",
    response_model=CartResponse,
)
def get_cart(
    cart_id: int = Path(
        ...,
        ge=1,
    ),
    db: Session = Depends(
        get_db,
    ),
    current_user: User = Depends(
        require_carts_manage,
    ),
):
    _ = current_user

    try:
        return CartService.get_cart(
            db=db,
            cart_id=cart_id,
        )
    except Exception as error:
        handle_cart_error(error)
