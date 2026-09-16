from __future__ import annotations

import math

from decimal import Decimal

from sqlalchemy import (
    String,
    cast,
    or_,
)
from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.branch import (
    Branch,
)
from app.models.cart_item import (
    CartItem,
)
from app.models.inventory import (
    Inventory,
)
from app.models.product_variant import (
    ProductVariant,
)
from app.models.shopping_cart import (
    ShoppingCart,
)
from app.models.user import (
    User,
)


class CartService:

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _money(
        value,
    ) -> Decimal:

        return Decimal(
            value
            or 0
        ).quantize(
            Decimal(
                "0.01"
            )
        )


    @staticmethod
    def _base_query(
        db: Session,
    ):

        return (
            db.query(
                ShoppingCart
            )
            .options(
                joinedload(
                    ShoppingCart.customer
                ),
                joinedload(
                    ShoppingCart.branch
                ),
                joinedload(
                    ShoppingCart.items
                )
                .joinedload(
                    CartItem.product_variant
                )
                .joinedload(
                    ProductVariant.product
                ),
                joinedload(
                    ShoppingCart.items
                )
                .joinedload(
                    CartItem.product_variant
                )
                .joinedload(
                    ProductVariant.size
                ),
                joinedload(
                    ShoppingCart.items
                )
                .joinedload(
                    CartItem.product_variant
                )
                .joinedload(
                    ProductVariant.color
                ),
            )
        )


    @staticmethod
    def _get_cart(
        db: Session,

        cart_id: int,
    ) -> ShoppingCart:

        cart = (
            CartService
            ._base_query(
                db
            )
            .filter(
                ShoppingCart.id
                ==
                cart_id
            )
            .first()
        )


        if cart is None:

            raise LookupError(
                "El carrito no existe."
            )


        return cart


    # =====================================================
    # CU32 - SERIALIZAR CARRITO
    # =====================================================

    @staticmethod
    def _serialize(
        cart: ShoppingCart,
    ) -> dict:

        items = []

        total_units = 0

        total_amount = Decimal(
            "0.00"
        )


        sorted_items = sorted(
            cart.items,

            key=lambda item:
                item.id,
        )


        for item in sorted_items:

            variant = (
                item.product_variant
            )


            base_price = (
                Decimal(
                    variant.product.base_price
                    or 0
                )
            )


            additional_price = (
                Decimal(
                    variant.additional_price
                    or 0
                )
            )


            unit_price = (
                base_price
                +
                additional_price
            ).quantize(
                Decimal(
                    "0.01"
                )
            )


            subtotal = (
                unit_price
                *
                item.quantity
            ).quantize(
                Decimal(
                    "0.01"
                )
            )


            total_units += (
                item.quantity
            )


            total_amount += (
                subtotal
            )


            items.append(
                {
                    "id":
                        item.id,

                    "cart_id":
                        item.cart_id,

                    "product_variant_id":
                        item.product_variant_id,

                    "quantity":
                        item.quantity,

                    "unit_price":
                        unit_price,

                    "subtotal":
                        subtotal,

                    "created_at":
                        item.created_at,

                    "updated_at":
                        item.updated_at,

                    "product_variant":
                        variant,
                }
            )


        return {
            "id":
                cart.id,

            "cart_code":
                f"CART-{cart.id:06d}",

            "customer_id":
                cart.customer_id,

            "branch_id":
                cart.branch_id,

            "status":
                cart.status,

            "created_at":
                cart.created_at,

            "updated_at":
                cart.updated_at,

            "total_items":
                len(
                    items
                ),

            "total_units":
                total_units,

            "total_amount":
                total_amount.quantize(
                    Decimal(
                        "0.01"
                    )
                ),

            "customer":
                cart.customer,

            "branch":
                cart.branch,

            "items":
                items,
        }


    # =====================================================
    # CU32 - LISTAR / FILTRAR CARRITOS
    # =====================================================

    @staticmethod
    def list_carts(
        db: Session,

        *,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        cart_status: str | None = None,
        branch_id: int | None = None,
        customer_id: int | None = None,
    ) -> dict:

        page = max(
            1,
            page,
        )


        page_size = max(
            1,
            min(
                page_size,
                100,
            ),
        )


        query = (
            CartService
            ._base_query(
                db
            )
            .join(
                User,
                ShoppingCart.customer_id
                ==
                User.id,
            )
        )


        # =================================================
        # ESTADO
        # =================================================

        if cart_status:

            query = (
                query.filter(
                    ShoppingCart.status
                    ==
                    cart_status
                )
            )


        # =================================================
        # SUCURSAL
        # =================================================

        if branch_id is not None:

            query = (
                query.filter(
                    ShoppingCart.branch_id
                    ==
                    branch_id
                )
            )


        # =================================================
        # CLIENTE
        # =================================================

        if customer_id is not None:

            query = (
                query.filter(
                    ShoppingCart.customer_id
                    ==
                    customer_id
                )
            )


        # =================================================
        # BÚSQUEDA
        #
        # Busca por:
        # - id/código virtual del carrito
        # - nombre
        # - apellido
        # - correo
        # =================================================

        if search:

            clean_search = (
                search.strip()
            )


            if clean_search:

                pattern = (
                    f"%{clean_search}%"
                )


                numeric_search = (
                    clean_search
                    .upper()
                    .replace(
                        "CART-",
                        "",
                    )
                    .strip()
                )


                conditions = [
                    User.first_name.ilike(
                        pattern
                    ),
                    User.last_name.ilike(
                        pattern
                    ),
                    User.email.ilike(
                        pattern
                    ),
                    cast(
                        ShoppingCart.id,
                        String,
                    ).ilike(
                        pattern
                    ),
                ]


                if numeric_search.isdigit():

                    conditions.append(
                        ShoppingCart.id
                        ==
                        int(
                            numeric_search
                        )
                    )


                query = (
                    query.filter(
                        or_(
                            *conditions
                        )
                    )
                )


        total = (
            query.count()
        )


        total_pages = (
            math.ceil(
                total
                /
                page_size
            )
            if total > 0
            else 0
        )


        carts = (
            query
            .order_by(
                ShoppingCart.updated_at.desc(),
                ShoppingCart.id.desc(),
            )
            .offset(
                (
                    page
                    -
                    1
                )
                *
                page_size
            )
            .limit(
                page_size
            )
            .all()
        )


        return {
            "items": [
                CartService
                ._serialize(
                    cart
                )

                for cart
                in carts
            ],

            "page":
                page,

            "page_size":
                page_size,

            "total":
                total,

            "total_pages":
                total_pages,
        }


    # =====================================================
    # CU32 - CONSULTAR CARRITO
    # =====================================================

    @staticmethod
    def get_cart(
        db: Session,

        *,
        cart_id: int,
    ) -> dict:

        cart = (
            CartService
            ._get_cart(
                db,
                cart_id,
            )
        )


        return (
            CartService
            ._serialize(
                cart
            )
        )


    # =====================================================
    # CU32 - HELPERS DEL CLIENTE
    # =====================================================

    @staticmethod
    def _validate_branch(
        db: Session,
        *,
        branch_id: int,
    ) -> Branch:
        branch = (
            db.query(Branch)
            .filter(
                Branch.id == branch_id,
                Branch.is_active.is_(True),
            )
            .first()
        )

        if branch is None:
            raise LookupError(
                "La sucursal no existe o está desactivada."
            )

        return branch


    @staticmethod
    def _get_variant_for_cart(
        db: Session,
        *,
        product_variant_id: int,
    ) -> ProductVariant:
        variant = (
            db.query(ProductVariant)
            .options(
                joinedload(ProductVariant.product),
                joinedload(ProductVariant.size),
                joinedload(ProductVariant.color),
            )
            .filter(
                ProductVariant.id == product_variant_id,
                ProductVariant.is_active.is_(True),
            )
            .first()
        )

        if variant is None:
            raise LookupError(
                "La variante del producto no existe o está desactivada."
            )

        if variant.product is None or not variant.product.is_active:
            raise ValueError(
                "El producto de esta variante no está disponible."
            )

        return variant


    @staticmethod
    def _available_stock(
        db: Session,
        *,
        branch_id: int,
        product_variant_id: int,
    ) -> int:
        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.branch_id == branch_id,
                Inventory.product_variant_id == product_variant_id,
                Inventory.is_active.is_(True),
            )
            .first()
        )

        if inventory is None:
            return 0

        return max(
            0,
            int(inventory.available_quantity),
        )


    @staticmethod
    def _get_active_cart_entity(
        db: Session,
        *,
        customer_id: int,
        branch_id: int,
    ) -> ShoppingCart | None:
        return (
            CartService
            ._base_query(db)
            .filter(
                ShoppingCart.customer_id == customer_id,
                ShoppingCart.branch_id == branch_id,
                ShoppingCart.status == "ACTIVE",
            )
            .order_by(ShoppingCart.id.desc())
            .first()
        )


    @staticmethod
    def _get_or_create_active_cart(
        db: Session,
        *,
        customer_id: int,
        branch_id: int,
    ) -> ShoppingCart:
        CartService._validate_branch(
            db,
            branch_id=branch_id,
        )

        cart = CartService._get_active_cart_entity(
            db,
            customer_id=customer_id,
            branch_id=branch_id,
        )

        if cart is not None:
            return cart

        cart = ShoppingCart(
            customer_id=customer_id,
            branch_id=branch_id,
            status="ACTIVE",
        )

        db.add(cart)
        db.flush()

        return cart


    @staticmethod
    def _get_owned_active_item(
        db: Session,
        *,
        customer_id: int,
        item_id: int,
    ) -> tuple[CartItem, ShoppingCart]:
        row = (
            db.query(CartItem, ShoppingCart)
            .join(
                ShoppingCart,
                CartItem.cart_id == ShoppingCart.id,
            )
            .filter(
                CartItem.id == item_id,
                ShoppingCart.customer_id == customer_id,
                ShoppingCart.status == "ACTIVE",
            )
            .first()
        )

        if row is None:
            raise LookupError(
                "El artículo no existe en tu carrito activo."
            )

        return row[0], row[1]


    # =====================================================
    # CU32 - CONSULTAR MI CARRITO
    # =====================================================

    @staticmethod
    def get_my_cart(
        db: Session,
        *,
        customer_id: int,
        branch_id: int,
    ) -> dict:
        CartService._validate_branch(
            db,
            branch_id=branch_id,
        )

        cart = CartService._get_active_cart_entity(
            db,
            customer_id=customer_id,
            branch_id=branch_id,
        )

        if cart is None:
            return {
                "branch_id": branch_id,
                "has_cart": False,
                "total_items": 0,
                "total_units": 0,
                "total_amount": Decimal("0.00"),
                "cart": None,
            }

        serialized = CartService._serialize(cart)

        return {
            "branch_id": branch_id,
            "has_cart": True,
            "total_items": serialized["total_items"],
            "total_units": serialized["total_units"],
            "total_amount": serialized["total_amount"],
            "cart": serialized,
        }


    # =====================================================
    # CU32 - CONTADOR DEL HEADER
    # =====================================================

    @staticmethod
    def get_my_cart_count(
        db: Session,
        *,
        customer_id: int,
        branch_id: int,
    ) -> dict:
        CartService._validate_branch(
            db,
            branch_id=branch_id,
        )

        cart = CartService._get_active_cart_entity(
            db,
            customer_id=customer_id,
            branch_id=branch_id,
        )

        if cart is None:
            return {
                "branch_id": branch_id,
                "total_items": 0,
                "total_units": 0,
            }

        return {
            "branch_id": branch_id,
            "total_items": len(cart.items),
            "total_units": sum(
                item.quantity
                for item in cart.items
            ),
        }


    # =====================================================
    # CU32 - AGREGAR AL CARRITO
    # =====================================================

    @staticmethod
    def add_item(
        db: Session,
        *,
        customer_id: int,
        branch_id: int,
        product_variant_id: int,
        quantity: int,
    ) -> dict:
        if quantity <= 0:
            raise ValueError(
                "La cantidad debe ser mayor a cero."
            )

        try:
            CartService._validate_branch(
                db,
                branch_id=branch_id,
            )

            CartService._get_variant_for_cart(
                db,
                product_variant_id=product_variant_id,
            )

            available = CartService._available_stock(
                db,
                branch_id=branch_id,
                product_variant_id=product_variant_id,
            )

            if available <= 0:
                raise ValueError(
                    "Esta variante no tiene stock disponible en la sucursal seleccionada."
                )

            cart = CartService._get_or_create_active_cart(
                db,
                customer_id=customer_id,
                branch_id=branch_id,
            )

            item = next(
                (
                    current
                    for current in cart.items
                    if current.product_variant_id == product_variant_id
                ),
                None,
            )

            new_quantity = quantity
            if item is not None:
                new_quantity = item.quantity + quantity

            if new_quantity > available:
                raise ValueError(
                    f"Solo hay {available} unidades disponibles de esta variante en la sucursal seleccionada."
                )

            if item is None:
                item = CartItem(
                    cart_id=cart.id,
                    product_variant_id=product_variant_id,
                    quantity=quantity,
                )
                db.add(item)
            else:
                item.quantity = new_quantity

            db.commit()

            refreshed = CartService._get_cart(
                db,
                cart.id,
            )

            return CartService._serialize(refreshed)

        except Exception:
            db.rollback()
            raise


    # =====================================================
    # CU32 - ACTUALIZAR CANTIDAD
    # =====================================================

    @staticmethod
    def update_item_quantity(
        db: Session,
        *,
        customer_id: int,
        item_id: int,
        quantity: int,
    ) -> dict:
        if quantity <= 0:
            raise ValueError(
                "La cantidad debe ser mayor a cero. Para quitar el producto usa la opción eliminar."
            )

        try:
            item, cart = CartService._get_owned_active_item(
                db,
                customer_id=customer_id,
                item_id=item_id,
            )

            if cart.branch_id is None:
                raise ValueError(
                    "El carrito no tiene una sucursal asociada."
                )

            available = CartService._available_stock(
                db,
                branch_id=cart.branch_id,
                product_variant_id=item.product_variant_id,
            )

            if quantity > available:
                raise ValueError(
                    f"Solo hay {available} unidades disponibles de esta variante en la sucursal del carrito."
                )

            item.quantity = quantity
            db.commit()

            refreshed = CartService._get_cart(
                db,
                cart.id,
            )

            return CartService._serialize(refreshed)

        except Exception:
            db.rollback()
            raise


    # =====================================================
    # CU32 - ELIMINAR UN PRODUCTO
    # =====================================================

    @staticmethod
    def remove_item(
        db: Session,
        *,
        customer_id: int,
        item_id: int,
    ) -> dict:
        try:
            item, cart = CartService._get_owned_active_item(
                db,
                customer_id=customer_id,
                item_id=item_id,
            )

            cart_id = cart.id
            db.delete(item)
            db.commit()

            refreshed = CartService._get_cart(
                db,
                cart_id,
            )

            return CartService._serialize(refreshed)

        except Exception:
            db.rollback()
            raise


    # =====================================================
    # CU32 - VACIAR CARRITO
    # =====================================================

    @staticmethod
    def clear_my_cart(
        db: Session,
        *,
        customer_id: int,
        branch_id: int,
    ) -> dict:
        CartService._validate_branch(
            db,
            branch_id=branch_id,
        )

        try:
            cart = CartService._get_active_cart_entity(
                db,
                customer_id=customer_id,
                branch_id=branch_id,
            )

            if cart is None:
                return {
                    "message": "Tu carrito ya está vacío.",
                    "branch_id": branch_id,
                    "removed_items": 0,
                    "total_items": 0,
                    "total_units": 0,
                }

            removed_items = len(cart.items)

            for item in list(cart.items):
                db.delete(item)

            db.commit()

            return {
                "message": "Carrito vaciado correctamente.",
                "branch_id": branch_id,
                "removed_items": removed_items,
                "total_items": 0,
                "total_units": 0,
            }

        except Exception:
            db.rollback()
            raise
