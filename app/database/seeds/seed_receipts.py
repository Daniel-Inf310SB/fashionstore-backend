from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product_variant import ProductVariant
from app.models.receipt import Receipt
from app.models.receipt_item import ReceiptItem
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User


def _money(value) -> Decimal:
    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01")
    )


def _customer_name(
    customer: User | None,
) -> str:

    if customer is None:
        return "Consumidor Final"

    full_name = " ".join(
        part
        for part in [
            customer.first_name,
            customer.last_name,
        ]
        if part
    ).strip()

    return full_name or customer.email


def _receipt_number(
    payment: Payment,
) -> str:

    # PAY-SEED-0001 -> CMP-SEED-0001
    return payment.payment_code.replace(
        "PAY-",
        "CMP-",
        1,
    )


def _create_receipt_item(
    db: Session,
    *,
    receipt: Receipt,
    product_variant_id: int,
    quantity: int,
    unit_price: Decimal,
    subtotal: Decimal,
) -> None:

    variant = db.get(
        ProductVariant,
        product_variant_id,
    )

    if variant is None:
        raise RuntimeError(
            f"No existe ProductVariant "
            f"{product_variant_id}."
        )

    if variant.product is None:
        raise RuntimeError(
            f"La variante {variant.id} "
            "no tiene producto."
        )

    item = ReceiptItem(
        receipt_id=receipt.id,

        # Snapshot histórico
        product_name=variant.product.name,
        sku=variant.sku,

        size_name=(
            variant.size.name
            if variant.size is not None
            else None
        ),

        color_name=(
            variant.color.name
            if variant.color is not None
            else None
        ),

        quantity=quantity,
        unit_price=_money(
            unit_price
        ),
        subtotal=_money(
            subtotal
        ),
    )

    db.add(
        item
    )


def _create_order_receipt(
    db: Session,
    *,
    payment: Payment,
    order: Order,
) -> Receipt:

    customer = db.get(
        User,
        order.customer_id,
    )

    if customer is None:
        raise RuntimeError(
            f"No existe el cliente "
            f"de la orden {order.order_code}."
        )

    receipt = Receipt(
        receipt_number=_receipt_number(
            payment
        ),

        receipt_type="ONLINE_PURCHASE",

        order_id=order.id,
        sale_id=None,

        customer_name=_customer_name(
            customer
        ),

        customer_email=customer.email,
        customer_document=(
            customer.document_number
        ),

        subtotal=_money(
            order.subtotal
        ),

        discount_amount=_money(
            order.discount_amount
        ),

        total_amount=_money(
            order.total_amount
        ),

        payment_method=(
            payment.payment_method
        ),

        currency=payment.currency,

        # El PDF todavía no existe.
        pdf_url=None,

        # Todavía no estamos enviando correo real.
        email_status=(
            "PENDING"
            if customer.email
            else "NOT_REQUESTED"
        ),

        emailed_at=None,
    )

    db.add(
        receipt
    )

    db.flush()

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
        raise RuntimeError(
            f"La orden {order.order_code} "
            "no tiene items."
        )

    for item in items:

        _create_receipt_item(
            db,
            receipt=receipt,
            product_variant_id=(
                item.product_variant_id
            ),
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal,
        )

    return receipt


def _create_sale_receipt(
    db: Session,
    *,
    payment: Payment,
    sale: Sale,
) -> Receipt:

    customer = None

    if sale.customer_id is not None:
        customer = db.get(
            User,
            sale.customer_id,
        )

    receipt = Receipt(
        receipt_number=_receipt_number(
            payment
        ),

        receipt_type="IN_STORE_SALE",

        order_id=None,
        sale_id=sale.id,

        customer_name=_customer_name(
            customer
        ),

        customer_email=(
            customer.email
            if customer is not None
            else None
        ),

        customer_document=(
            customer.document_number
            if customer is not None
            else None
        ),

        subtotal=_money(
            sale.subtotal
        ),

        discount_amount=_money(
            sale.discount_amount
        ),

        total_amount=_money(
            sale.total_amount
        ),

        payment_method=(
            payment.payment_method
        ),

        currency=payment.currency,

        pdf_url=None,

        email_status=(
            "PENDING"
            if (
                customer is not None
                and customer.email
            )
            else "NOT_REQUESTED"
        ),

        emailed_at=None,
    )

    db.add(
        receipt
    )

    db.flush()

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
        raise RuntimeError(
            f"La venta {sale.sale_code} "
            "no tiene items."
        )

    for item in items:

        _create_receipt_item(
            db,
            receipt=receipt,
            product_variant_id=(
                item.product_variant_id
            ),
            quantity=item.quantity,
            unit_price=item.unit_price,
            subtotal=item.subtotal,
        )

    return receipt


def seed_receipts(
    db: Session,
) -> None:

    print(
        "🌱 Seed comprobantes..."
    )

    payments = list(
        db.scalars(
            select(Payment)
            .where(
                Payment.payment_code.like(
                    "PAY-SEED-%"
                ),
                Payment.status
                == "APPROVED",
            )
            .order_by(
                Payment.payment_code
            )
        ).all()
    )

    if not payments:
        raise RuntimeError(
            "No existen pagos APPROVED seed. "
            "Ejecuta seed_payments primero."
        )

    created = 0
    existing = 0
    created_items = 0

    for payment in payments:

        number = _receipt_number(
            payment
        )

        # =================================================
        # IDEMPOTENCIA
        # =================================================

        receipt = db.scalar(
            select(Receipt)
            .where(
                Receipt.receipt_number
                == number
            )
        )

        if receipt is not None:
            existing += 1
            continue

        # =================================================
        # ORDER
        # =================================================

        if payment.order_id is not None:

            order = db.get(
                Order,
                payment.order_id,
            )

            if order is None:
                raise RuntimeError(
                    f"El pago "
                    f"{payment.payment_code} "
                    "apunta a una orden "
                    "inexistente."
                )

            if order.status != "PAID":
                raise RuntimeError(
                    f"La orden "
                    f"{order.order_code} "
                    "no está PAID."
                )

            receipt = (
                _create_order_receipt(
                    db,
                    payment=payment,
                    order=order,
                )
            )

        # =================================================
        # SALE
        # =================================================

        elif payment.sale_id is not None:

            sale = db.get(
                Sale,
                payment.sale_id,
            )

            if sale is None:
                raise RuntimeError(
                    f"El pago "
                    f"{payment.payment_code} "
                    "apunta a una venta "
                    "inexistente."
                )

            if sale.status != "PAID":
                raise RuntimeError(
                    f"La venta "
                    f"{sale.sale_code} "
                    "no está PAID."
                )

            receipt = (
                _create_sale_receipt(
                    db,
                    payment=payment,
                    sale=sale,
                )
            )

        else:
            raise RuntimeError(
                f"El pago "
                f"{payment.payment_code} "
                "no tiene Order ni Sale."
            )

        db.flush()

        item_count = len(
            receipt.items
        )

        created_items += item_count
        created += 1

    db.flush()

    print(
        "✅ Comprobantes listos: "
        f"{created} creados, "
        f"{existing} ya existentes, "
        f"{created_items} items creados."
    )


# =========================================================
# EJECUCION DIRECTA
# =========================================================

if __name__ == "__main__":

    from app.database.session import (
        SessionLocal,
    )

    from app.database.seeds.seed_orders import (
        seed_orders,
    )

    from app.database.seeds.seed_sales import (
        seed_sales,
    )

    from app.database.seeds.seed_payments import (
        seed_payments,
    )

    db = SessionLocal()

    try:

        seed_orders(
            db
        )

        seed_sales(
            db
        )

        seed_payments(
            db
        )

        seed_receipts(
            db
        )

        db.commit()

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()