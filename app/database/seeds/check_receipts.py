from __future__ import annotations

from decimal import Decimal

from sqlalchemy import func, select

from app.database.session import SessionLocal
from app.models.inventory_movement import InventoryMovement
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product_variant import ProductVariant
from app.models.receipt import Receipt
from app.models.receipt_item import ReceiptItem
from app.models.sale import Sale
from app.models.sale_item import SaleItem


def _money(value) -> Decimal:
    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01")
    )


def check_receipts() -> None:

    db = SessionLocal()

    try:

        print()
        print("=" * 70)
        print(
            "VERIFICACION - ITERACION 2 / "
            "COMPROBANTES"
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

        for payment in payments:

            print()
            print("-" * 70)

            print(
                f"{payment.payment_code}"
                f" | {payment.status}"
            )

            receipt = None
            source_items = []
            source_total = None
            source_subtotal = None
            source_discount = None

            # =============================================
            # ORDER
            # =============================================

            if payment.order_id is not None:

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

                receipt = db.scalar(
                    select(Receipt)
                    .where(
                        Receipt.order_id
                        == order.id
                    )
                )

                source_items = list(
                    db.scalars(
                        select(OrderItem)
                        .where(
                            OrderItem.order_id
                            == order.id
                        )
                    ).all()
                )

                source_total = (
                    order.total_amount
                )

                source_subtotal = (
                    order.subtotal
                )

                source_discount = (
                    order.discount_amount
                )

                print(
                    f"Orden: "
                    f"{order.order_code}"
                )

            # =============================================
            # SALE
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

                receipt = db.scalar(
                    select(Receipt)
                    .where(
                        Receipt.sale_id
                        == sale.id
                    )
                )

                source_items = list(
                    db.scalars(
                        select(SaleItem)
                        .where(
                            SaleItem.sale_id
                            == sale.id
                        )
                    ).all()
                )

                source_total = (
                    sale.total_amount
                )

                source_subtotal = (
                    sale.subtotal
                )

                source_discount = (
                    sale.discount_amount
                )

                print(
                    f"Venta: "
                    f"{sale.sale_code}"
                )

            # =============================================
            # APPROVED DEBE TENER RECEIPT
            # =============================================

            if payment.status == "APPROVED":

                if receipt is None:
                    errors += 1

                    print(
                        "❌ Pago aprobado sin "
                        "comprobante"
                    )

                    continue

                print(
                    f"Comprobante: "
                    f"{receipt.receipt_number}"
                )

                print(
                    f"Tipo: "
                    f"{receipt.receipt_type}"
                )

                print(
                    f"Cliente: "
                    f"{receipt.customer_name}"
                )

                print(
                    f"Email: "
                    f"{receipt.customer_email}"
                )

                print(
                    f"Estado email: "
                    f"{receipt.email_status}"
                )

                print(
                    f"Subtotal: "
                    f"{receipt.subtotal}"
                )

                print(
                    f"Descuento: "
                    f"{receipt.discount_amount}"
                )

                print(
                    f"Total: "
                    f"{receipt.total_amount}"
                )

                print(
                    f"Metodo pago: "
                    f"{receipt.payment_method}"
                )

                if (
                    _money(
                        receipt.total_amount
                    )
                    != _money(
                        source_total
                    )
                ):
                    errors += 1
                    print(
                        "❌ Total del comprobante "
                        "no coincide"
                    )

                if (
                    _money(
                        receipt.subtotal
                    )
                    != _money(
                        source_subtotal
                    )
                ):
                    errors += 1
                    print(
                        "❌ Subtotal incorrecto"
                    )

                if (
                    _money(
                        receipt.discount_amount
                    )
                    != _money(
                        source_discount
                    )
                ):
                    errors += 1
                    print(
                        "❌ Descuento incorrecto"
                    )

                if (
                    receipt.payment_method
                    != payment.payment_method
                ):
                    errors += 1
                    print(
                        "❌ Metodo de pago "
                        "incorrecto"
                    )

                if (
                    receipt.currency
                    != payment.currency
                ):
                    errors += 1
                    print(
                        "❌ Moneda incorrecta"
                    )

                receipt_items = list(
                    db.scalars(
                        select(ReceiptItem)
                        .where(
                            ReceiptItem.receipt_id
                            == receipt.id
                        )
                    ).all()
                )

                print(
                    f"Items comprobante: "
                    f"{len(receipt_items)}"
                )

                if (
                    len(receipt_items)
                    != len(source_items)
                ):
                    errors += 1

                    print(
                        "❌ Cantidad de items "
                        "no coincide"
                    )

                receipt_by_sku = {
                    item.sku: item
                    for item
                    in receipt_items
                }

                for source_item in source_items:

                    variant = db.get(
                        ProductVariant,
                        source_item
                        .product_variant_id,
                    )

                    if variant is None:
                        errors += 1
                        print(
                            "❌ Variante inexistente"
                        )
                        continue

                    receipt_item = (
                        receipt_by_sku.get(
                            variant.sku
                        )
                    )

                    if receipt_item is None:
                        errors += 1

                        print(
                            f"❌ SKU "
                            f"{variant.sku} "
                            "no está en comprobante"
                        )

                        continue

                    print(
                        f"  {receipt_item.sku}"
                        f" | "
                        f"{receipt_item.product_name}"
                        f" | "
                        f"{receipt_item.quantity}"
                        f" x "
                        f"{receipt_item.unit_price}"
                        f" = "
                        f"{receipt_item.subtotal}"
                    )

                    if (
                        receipt_item.quantity
                        != source_item.quantity
                    ):
                        errors += 1
                        print(
                            "    ❌ Cantidad "
                            "incorrecta"
                        )

                    if (
                        _money(
                            receipt_item.unit_price
                        )
                        != _money(
                            source_item.unit_price
                        )
                    ):
                        errors += 1

                        print(
                            "    ❌ Precio "
                            "incorrecto"
                        )

                    if (
                        _money(
                            receipt_item.subtotal
                        )
                        != _money(
                            source_item.subtotal
                        )
                    ):
                        errors += 1

                        print(
                            "    ❌ Subtotal item "
                            "incorrecto"
                        )

                    if (
                        receipt_item.product_name
                        != variant.product.name
                    ):
                        errors += 1

                        print(
                            "    ❌ Nombre histórico "
                            "incorrecto"
                        )

                    if (
                        receipt_item.sku
                        != variant.sku
                    ):
                        errors += 1

                        print(
                            "    ❌ SKU histórico "
                            "incorrecto"
                        )

            # =============================================
            # REJECTED / FAILED NO DEBE TENER RECEIPT
            # =============================================

            elif payment.status in {
                "REJECTED",
                "FAILED",
            }:

                if receipt is not None:
                    errors += 1

                    print(
                        "❌ Pago rechazado/failed "
                        "tiene comprobante"
                    )

                else:
                    print(
                        "✅ Sin comprobante, "
                        "como corresponde."
                    )

        # =================================================
        # RECEIPT NO DEBE MOVER INVENTARIO
        # =================================================

        receipt_movements = db.scalar(
            select(
                func.count(
                    InventoryMovement.id
                )
            )
            .where(
                InventoryMovement.reference_type
                == "RECEIPT"
            )
        )

        print()
        print(
            "Movimientos de inventario "
            f"RECEIPT: {receipt_movements}"
        )

        if receipt_movements != 0:
            errors += 1

            print(
                "❌ Crear comprobantes "
                "modificó inventario."
            )

        print()
        print("=" * 70)

        if errors == 0:

            print(
                "✅ TODO CORRECTO"
            )

            print(
                "Los comprobantes corresponden "
                "solo a pagos aprobados y "
                "conservan correctamente los "
                "datos históricos de la compra."
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
    check_receipts()