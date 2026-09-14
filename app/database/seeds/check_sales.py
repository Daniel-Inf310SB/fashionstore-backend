from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models.inventory_movement import InventoryMovement
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User


def _money(value) -> Decimal:
    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01")
    )


def check_sales() -> None:

    db = SessionLocal()

    try:

        print()
        print("=" * 70)
        print(
            "VERIFICACION - ITERACION 2 / "
            "VENTAS PRESENCIALES"
        )
        print("=" * 70)

        sales = list(
            db.scalars(
                select(Sale)
                .where(
                    Sale.sale_code.like(
                        "VTA-SEED-%"
                    )
                )
                .order_by(
                    Sale.sale_code
                )
            ).all()
        )

        if not sales:
            print(
                "❌ No existen ventas seed."
            )
            return

        errors = 0

        print(
            f"\nVentas encontradas: "
            f"{len(sales)}"
        )

        for sale in sales:

            print()
            print("-" * 70)

            print(
                f"{sale.sale_code}"
                f" | {sale.status}"
            )

            cashier = db.get(
                User,
                sale.cashier_id,
            )

            if cashier is None:
                errors += 1
                print(
                    "❌ Cajero inexistente"
                )
            else:
                print(
                    f"Cajero: "
                    f"{cashier.first_name} "
                    f"{cashier.last_name or ''}"
                )

            if sale.customer_id is None:
                print(
                    "Cliente: venta sin "
                    "cliente registrado"
                )
            else:

                customer = db.get(
                    User,
                    sale.customer_id,
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
                    select(SaleItem)
                    .where(
                        SaleItem.sale_id
                        == sale.id
                    )
                    .order_by(
                        SaleItem.id
                    )
                ).all()
            )

            if not items:
                errors += 1
                print(
                    "❌ Venta sin items"
                )
                continue

            calculated_subtotal = (
                Decimal("0.00")
            )

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
                        "en la venta"
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
                        "  ❌ Subtotal item "
                        "incorrecto"
                    )

                calculated_subtotal += (
                    item.subtotal
                )

            calculated_subtotal = _money(
                calculated_subtotal
            )

            expected_total = _money(
                sale.subtotal
                - sale.discount_amount
            )

            print()
            print(
                f"Subtotal BD: "
                f"{sale.subtotal}"
            )

            print(
                f"Subtotal calculado: "
                f"{calculated_subtotal}"
            )

            print(
                f"Descuento: "
                f"{sale.discount_amount}"
            )

            print(
                f"Total: "
                f"{sale.total_amount}"
            )

            if (
                _money(sale.subtotal)
                != calculated_subtotal
            ):
                errors += 1
                print(
                    "❌ Subtotal no coincide "
                    "con items"
                )

            if (
                _money(sale.total_amount)
                != expected_total
            ):
                errors += 1
                print(
                    "❌ Total incorrecto"
                )

            if sale.status != "PENDING":
                errors += 1

                print(
                    "❌ La venta todavía "
                    "no debería estar pagada"
                )

        # =================================================
        # TODAVÍA NO DEBE HABER SALE DE ESTAS VENTAS
        # =================================================

        movements = db.scalar(
            select(
                func.count(
                    InventoryMovement.id
                )
            )
            .where(
                InventoryMovement.reference_type
                == "SALE",
                InventoryMovement.reference_code.like(
                    "VTA-SEED-%"
                ),
                InventoryMovement.movement_type
                == "SALE",
            )
        )

        print()
        print(
            "Movimientos SALE de ventas "
            f"seed: {movements}"
        )

        if movements != 0:
            errors += 1

            print(
                "❌ Se descontó inventario "
                "antes del pago."
            )

        print()
        print("=" * 70)

        if errors == 0:

            print(
                "✅ TODO CORRECTO"
            )

            print(
                "Ventas, items, subtotales "
                "y totales son coherentes."
            )

            print(
                "El inventario todavía no "
                "fue descontado."
            )

        else:

            print(
                f"❌ SE ENCONTRARON "
                f"{errors} PROBLEMAS"
            )

        print("=" * 70)

    finally:

        db.close()


if __name__ == "__main__":
    check_sales()