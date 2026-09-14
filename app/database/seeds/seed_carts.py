from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.cart_item import CartItem
from app.models.inventory import Inventory
from app.models.shopping_cart import ShoppingCart
from app.models.user import User


# =========================================================
# CLIENTES Y ESCENARIOS DEL SEED
# =========================================================

CART_SCENARIOS = [
    {
        "email": "cliente01@fashionstore.com",
        "status": "ACTIVE",
        "quantities": [1, 2],
    },
    {
        "email": "cliente02@fashionstore.com",
        "status": "ACTIVE",
        "quantities": [1, 1, 2],
    },
    {
        "email": "cliente03@fashionstore.com",
        "status": "CONVERTED",
        "quantities": [2, 1],
    },
    {
        "email": "cliente04@fashionstore.com",
        "status": "ABANDONED",
        "quantities": [1, 1],
    },
]


def _get_customer(
    db: Session,
    email: str,
) -> User:

    customer = db.scalar(
        select(User)
        .where(
            User.email == email
        )
    )

    if customer is None:
        raise RuntimeError(
            f"No existe el cliente {email}. "
            "Ejecuta seed_customers primero."
        )

    return customer


def _get_available_inventories(
    db: Session,
    *,
    minimum_available: int = 5,
) -> list[Inventory]:

    inventories = list(
        db.scalars(
            select(Inventory)
            .where(
                Inventory.is_active.is_(True),
                (
                    Inventory.stock_quantity
                    - Inventory.reserved_quantity
                ) >= minimum_available,
            )
            .order_by(
                Inventory.id
            )
        ).all()
    )

    if not inventories:
        raise RuntimeError(
            "No existe inventario suficiente "
            "para crear carritos de prueba."
        )

    return inventories


def seed_carts(
    db: Session,
) -> None:

    print(
        "🌱 Seed carritos..."
    )

    inventories = _get_available_inventories(
        db
    )

    created_carts = 0
    existing_carts = 0
    created_items = 0

    inventory_index = 0

    for scenario in CART_SCENARIOS:

        customer = _get_customer(
            db,
            scenario["email"],
        )

        # =================================================
        # IDEMPOTENCIA
        # =================================================

        cart = db.scalar(
            select(ShoppingCart)
            .where(
                ShoppingCart.customer_id
                == customer.id,
                ShoppingCart.status
                == scenario["status"],
            )
            .order_by(
                ShoppingCart.id
            )
        )

        if cart is not None:
            existing_carts += 1
            continue

        # =================================================
        # CREAR CARRITO
        # =================================================

        cart = ShoppingCart(
            customer_id=customer.id,
            status=scenario["status"],
        )

        db.add(
            cart
        )

        db.flush()

        created_carts += 1

        used_variant_ids: set[int] = set()

        # =================================================
        # CREAR ITEMS
        # =================================================

        for quantity in scenario["quantities"]:

            found_inventory = None

            attempts = 0

            while attempts < len(inventories):

                inventory = inventories[
                    inventory_index
                    % len(inventories)
                ]

                inventory_index += 1
                attempts += 1

                if (
                    inventory.product_variant_id
                    in used_variant_ids
                ):
                    continue

                available = (
                    inventory.stock_quantity
                    - inventory.reserved_quantity
                )

                if available < quantity:
                    continue

                found_inventory = inventory
                break

            if found_inventory is None:
                raise RuntimeError(
                    "No se encontró una variante "
                    "con stock suficiente para "
                    "el carrito."
                )

            used_variant_ids.add(
                found_inventory.product_variant_id
            )

            item = CartItem(
                cart_id=cart.id,
                product_variant_id=(
                    found_inventory.product_variant_id
                ),
                quantity=quantity,
            )

            db.add(
                item
            )

            created_items += 1

    db.flush()

    print(
        "✅ Carritos listos: "
        f"{created_carts} creados, "
        f"{existing_carts} ya existentes, "
        f"{created_items} items creados."
    )


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================

if __name__ == "__main__":

    from app.database.session import SessionLocal
    from app.database.seeds.seed_customers import (
        seed_customers,
    )

    db = SessionLocal()

    try:

        seed_customers(
            db
        )

        seed_carts(
            db
        )

        db.commit()

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()