from __future__ import annotations

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.inventory_movement import InventoryMovement
from app.models.order import Order
from app.models.payment import Payment
from app.models.sale import Sale


def check_payments() -> None:

    db = SessionLocal()

    try:

        print()
        print("=" * 70)
        print(
            "VERIFICACION - ITERACION 2 / PAGOS"
        )
        print("=" * 70)

        payments = list(
            db.scalars(
                select(Payment)
                .where(
                    Payment.payment_code.like(
                        "PAY-SEED-%"
                    )
                )
                .order_by(
                    Payment.payment_code
                )
            ).all()
        )

        if not payments:
            print(
                "❌ No existen pagos seed."
            )
            return

        errors = 0

        print(
            f"\nPagos encontrados: "
            f"{len(payments)}"
        )

        for payment in payments:

            print()
            print("-" * 70)

            print(
                f"{payment.payment_code}"
                f" | {payment.status}"
            )

            print(
                f"Metodo: "
                f"{payment.payment_method}"
            )

            print(
                f"Canal: "
                f"{payment.channel}"
            )

            print(
                f"Monto: "
                f"{payment.amount} "
                f"{payment.currency}"
            )

            # =============================================
            # ORDEN
            # =============================================

            if payment.order_id is not None:

                if payment.sale_id is not None:
                    errors += 1
                    print(
                        "❌ Pago tiene Order y "
                        "Sale simultaneamente"
                    )

                order = db.get(
                    Order,
                    payment.order_id,
                )

                if order is None:
                    errors += 1
                    print(
                        "❌ Orden inexistente"
                    )
                    continue

                print(
                    f"Orden: "
                    f"{order.order_code}"
                )

                print(
                    f"Estado orden: "
                    f"{order.status}"
                )

                movements = list(
                    db.scalars(
                        select(
                            InventoryMovement
                        )
                        .where(
                            InventoryMovement
                            .reference_type
                            == "ORDER",
                            InventoryMovement
                            .reference_id
                            == order.id,
                            InventoryMovement
                            .movement_type
                            == "SALE",
                        )
                    ).all()
                )

                if payment.status == "APPROVED":

                    if order.status != "PAID":
                        errors += 1
                        print(
                            "❌ Pago aprobado pero "
                            "orden no esta PAID"
                        )

                    if not movements:
                        errors += 1
                        print(
                            "❌ Pago aprobado sin "
                            "SALE de inventario"
                        )

                elif payment.status in {
                    "REJECTED",
                    "FAILED",
                }:

                    if movements:
                        errors += 1
                        print(
                            "❌ Pago rechazado/failed "
                            "desconto inventario"
                        )

                    if (
                        order.status
                        != "PAYMENT_FAILED"
                    ):
                        errors += 1
                        print(
                            "❌ Orden rechazada no "
                            "esta PAYMENT_FAILED"
                        )

                print(
                    f"Movimientos SALE: "
                    f"{len(movements)}"
                )

            # =============================================
            # VENTA PRESENCIAL
            # =============================================

            elif payment.sale_id is not None:

                sale = db.get(
                    Sale,
                    payment.sale_id,
                )

                if sale is None:
                    errors += 1
                    print(
                        "❌ Venta inexistente"
                    )
                    continue

                print(
                    f"Venta: "
                    f"{sale.sale_code}"
                )

                print(
                    f"Estado venta: "
                    f"{sale.status}"
                )

                movements = list(
                    db.scalars(
                        select(
                            InventoryMovement
                        )
                        .where(
                            InventoryMovement
                            .reference_type
                            == "SALE",
                            InventoryMovement
                            .reference_id
                            == sale.id,
                            InventoryMovement
                            .movement_type
                            == "SALE",
                        )
                    ).all()
                )

                if payment.status == "APPROVED":

                    if sale.status != "PAID":
                        errors += 1
                        print(
                            "❌ Pago aprobado pero "
                            "venta no esta PAID"
                        )

                    if not movements:
                        errors += 1
                        print(
                            "❌ Venta aprobada sin "
                            "movimiento SALE"
                        )

                elif payment.status in {
                    "REJECTED",
                    "FAILED",
                }:

                    if movements:
                        errors += 1
                        print(
                            "❌ Pago rechazado "
                            "desconto inventario"
                        )

                print(
                    f"Movimientos SALE: "
                    f"{len(movements)}"
                )

            else:

                errors += 1

                print(
                    "❌ Pago sin Order ni Sale"
                )

        # =================================================
        # VALIDAR MOVIMIENTOS
        # =================================================

        movements = list(
            db.scalars(
                select(InventoryMovement)
                .where(
                    InventoryMovement
                    .movement_type
                    == "SALE",
                    InventoryMovement
                    .reference_code.like(
                        "%-SEED-%"
                    ),
                )
                .order_by(
                    InventoryMovement.id
                )
            ).all()
        )

        print()
        print("=" * 70)
        print(
            "MOVIMIENTOS DE INVENTARIO"
        )
        print("=" * 70)

        for movement in movements:

            print(
                f"{movement.reference_code}"
                f" | {movement.movement_type}"
                f" | cantidad="
                f"{movement.quantity}"
                f" | stock "
                f"{movement.stock_before}"
                f" -> "
                f"{movement.stock_after}"
                f" | reservado "
                f"{movement.reserved_before}"
                f" -> "
                f"{movement.reserved_after}"
            )

            if (
                movement.stock_after
                != (
                    movement.stock_before
                    - movement.quantity
                )
            ):
                errors += 1
                print(
                    "❌ Movimiento SALE "
                    "con stock incoherente"
                )

            if (
                movement.reserved_before
                != movement.reserved_after
            ):
                errors += 1
                print(
                    "❌ SALE modifico "
                    "reserved_quantity"
                )

        print()
        print("=" * 70)

        if errors == 0:

            print(
                "✅ TODO CORRECTO"
            )

            print(
                "Pagos aprobados descuentan "
                "inventario y pagos rechazados "
                "no lo modifican."
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
    check_payments()