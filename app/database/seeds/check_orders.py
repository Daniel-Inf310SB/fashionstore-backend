from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models.inventory_movement import InventoryMovement
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.user import User


def _money(value) -> Decimal:
    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01")
    )


def check_orders() -> None:

    db = SessionLocal()

    try:

        print()
        print("=" * 70)
        print(
            "VERIFICACION - ITERACION 2 / "
            "COMPRAS DIGITALES"
        )
        print("=" * 70)

        orders = list(
            db.scalars(
                select(Order)
                .where(
                    Order.order_code.like(
                        "ORD-SEED-%"
                    )
                )
                .order_by(
                    Order.order_code
                )
            ).all()
        )

        if not orders:
            print(
                "❌ No existen órdenes seed."
            )
            return

        errors = 0

        print(
            f"\nOrdenes encontradas: "
            f"{len(orders)}"
        )

        for order in orders:

            print()
            print("-" * 70)

            print(
                f"{order.order_code}"
                f" | {order.status}"
            )

            customer = db.get(
                User,
                order.customer_id,
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
                    select(OrderItem)
                    .where(
                        OrderItem.order_id
                        == order.id
                    )
                    .order_by(
                        OrderItem.id
                    )
                ).all()
            )

            if not items:
                errors += 1
                print(
                    "❌ Orden sin items"
                )
                continue

            calculated_subtotal = (
                Decimal("0.00")
            )

            seen_variants: set[int] = set()

            print(
                f"Items: {len(items)}"
            )

            for item in items:

                if (
                    item.product_variant_id
                    in seen_variants
                ):
                    errors += 1
                    print(
                        "❌ Variante duplicada "
                        "en la orden"
                    )

                seen_variants.add(
                    item.product_variant_id
                )

                expected_item_subtotal = _money(
                    item.unit_price
                    * item.quantity
                )

                print(
                    f"  Variante "
                    f"{item.product_variant_id}"
                )

                print(
                    f"  {item.quantity} x "
                    f"{item.unit_price} = "
                    f"{item.subtotal}"
                )

                if (
                    _money(item.subtotal)
                    != expected_item_subtotal
                ):
                    errors += 1
                    print(
                        "  ❌ Subtotal del item "
                        "incorrecto"
                    )

                calculated_subtotal += (
                    item.subtotal
                )

            calculated_subtotal = _money(
                calculated_subtotal
            )

            expected_total = _money(
                order.subtotal
                - order.discount_amount
            )

            print()
            print(
                f"Subtotal BD: "
                f"{order.subtotal}"
            )

            print(
                f"Subtotal calculado: "
                f"{calculated_subtotal}"
            )

            print(
                f"Descuento: "
                f"{order.discount_amount}"
            )

            print(
                f"Total: "
                f"{order.total_amount}"
            )

            if (
                _money(order.subtotal)
                != calculated_subtotal
            ):
                errors += 1
                print(
                    "❌ El subtotal de la orden "
                    "no coincide con sus items"
                )

            if (
                _money(order.total_amount)
                != expected_total
            ):
                errors += 1
                print(
                    "❌ Total incorrecto"
                )

            if order.total_amount < 0:
                errors += 1
                print(
                    "❌ Total negativo"
                )

            if (
                order.status
                != "PENDING_PAYMENT"
            ):
                errors += 1
                print(
                    "❌ La orden seed aún no "
                    "debería estar pagada."
                )

        # =================================================
        # TODAVÍA NO DEBE EXISTIR SALE DE ORDER
        # =================================================

        sale_movements = db.scalar(
            select(
                func.count(
                    InventoryMovement.id
                )
            )
            .where(
                InventoryMovement.reference_type
                == "ORDER",
                InventoryMovement.reference_code.like(
                    "ORD-SEED-%"
                ),
                InventoryMovement.movement_type
                == "SALE",
            )
        )

        print()
        print(
            "Movimientos SALE de órdenes "
            f"seed: {sale_movements}"
        )

        if sale_movements != 0:
            errors += 1

            print(
                "❌ Las órdenes están "
                "descontando inventario antes "
                "del pago."
            )

        print()
        print("=" * 70)

        if errors == 0:

            print(
                "✅ TODO CORRECTO"
            )

            print(
                "Ordenes, items, subtotales, "
                "descuentos y totales son "
                "coherentes."
            )

            print(
                "El inventario todavía no fue "
                "descontado, como corresponde."
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
    check_orders()