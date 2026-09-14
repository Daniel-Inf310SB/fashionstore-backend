from __future__ import annotations

from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models.cart_item import CartItem
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.shopping_cart import ShoppingCart
from app.models.user import User


CUSTOMER_EMAILS = [
    "cliente01@fashionstore.com",
    "cliente02@fashionstore.com",
    "cliente03@fashionstore.com",
    "cliente04@fashionstore.com",
]


def check_carts() -> None:

    db = SessionLocal()

    try:

        print()
        print("=" * 70)
        print("VERIFICACION - ITERACION 2 / CARRITOS")
        print("=" * 70)

        errors = 0

        customers = list(
            db.scalars(
                select(User)
                .where(
                    User.email.in_(
                        CUSTOMER_EMAILS
                    )
                )
            ).all()
        )

        if not customers:
            print(
                "❌ No existen clientes seed."
            )
            return

        customer_ids = [
            customer.id
            for customer in customers
        ]

        carts = list(
            db.scalars(
                select(ShoppingCart)
                .where(
                    ShoppingCart.customer_id.in_(
                        customer_ids
                    )
                )
                .order_by(
                    ShoppingCart.id
                )
            ).all()
        )

        if not carts:
            print(
                "❌ No existen carritos seed."
            )
            return

        print(
            f"\nCarritos encontrados: "
            f"{len(carts)}"
        )

        for cart in carts:

            customer = db.get(
                User,
                cart.customer_id,
            )

            print()
            print("-" * 70)

            print(
                f"Cart ID: {cart.id}"
                f" | Estado: {cart.status}"
            )

            if customer is None:
                errors += 1
                print(
                    "❌ Cliente inexistente"
                )
            else:
                print(
                    f"Cliente: "
                    f"{customer.first_name} "
                    f"{customer.last_name or ''}"
                )

            items = list(
                db.scalars(
                    select(CartItem)
                    .where(
                        CartItem.cart_id
                        == cart.id
                    )
                    .order_by(
                        CartItem.id
                    )
                ).all()
            )

            if not items:
                errors += 1
                print(
                    "❌ Carrito sin items"
                )
                continue

            print(
                f"Items: {len(items)}"
            )

            seen_variants: set[int] = set()

            for item in items:

                if (
                    item.product_variant_id
                    in seen_variants
                ):
                    errors += 1

                    print(
                        "❌ Variante duplicada "
                        "dentro del carrito"
                    )

                seen_variants.add(
                    item.product_variant_id
                )

                inventory = db.scalar(
                    select(Inventory)
                    .where(
                        Inventory.product_variant_id
                        == item.product_variant_id,
                        Inventory.is_active.is_(True),
                    )
                    .order_by(
                        Inventory.id
                    )
                )

                print(
                    f"  Variante: "
                    f"{item.product_variant_id}"
                )

                print(
                    f"  Cantidad carrito: "
                    f"{item.quantity}"
                )

                if item.quantity <= 0:
                    errors += 1
                    print(
                        "  ❌ Cantidad inválida"
                    )

                if inventory is None:
                    errors += 1
                    print(
                        "  ❌ Variante sin inventario"
                    )
                    continue

                available = (
                    inventory.stock_quantity
                    - inventory.reserved_quantity
                )

                print(
                    f"  Stock: "
                    f"{inventory.stock_quantity}"
                )

                print(
                    f"  Reservado: "
                    f"{inventory.reserved_quantity}"
                )

                print(
                    f"  Disponible: "
                    f"{available}"
                )

        # =================================================
        # EL CARRITO NO DEBE GENERAR MOVIMIENTOS
        # =================================================

        cart_movements = db.scalar(
            select(
                func.count(
                    InventoryMovement.id
                )
            )
            .where(
                InventoryMovement.reference_type
                == "CART"
            )
        )

        print()
        print(
            f"Movimientos de inventario CART: "
            f"{cart_movements}"
        )

        if cart_movements != 0:
            errors += 1

            print(
                "❌ El carrito está generando "
                "movimientos de inventario."
            )

        print()
        print("=" * 70)

        if errors == 0:

            print(
                "✅ TODO CORRECTO"
            )

            print(
                "Los carritos e items son "
                "coherentes y no modifican "
                "el inventario."
            )

        else:

            print(
                f"❌ SE ENCONTRARON "
                f"{errors} PROBLEMAS"
            )

        print("=" * 70)
        print()

    finally:

        db.close()


if __name__ == "__main__":
    check_carts()