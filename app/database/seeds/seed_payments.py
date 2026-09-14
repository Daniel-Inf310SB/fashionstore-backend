from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.sale import Sale
from app.models.sale_item import SaleItem


PAYMENT_SCENARIOS = [
    # =====================================================
    # COMPRAS DIGITALES
    # =====================================================
    {
        "code": "PAY-SEED-0001",
        "source_type": "ORDER",
        "source_code": "ORD-SEED-0001",
        "payment_method": "QR",
        "channel": "ONLINE",
        "provider": "TEST",
        "status": "APPROVED",
    },
    {
        "code": "PAY-SEED-0002",
        "source_type": "ORDER",
        "source_code": "ORD-SEED-0002",
        "payment_method": "CARD",
        "channel": "ONLINE",
        "provider": "TEST",
        "status": "APPROVED",
    },
    {
        "code": "PAY-SEED-0003",
        "source_type": "ORDER",
        "source_code": "ORD-SEED-0003",
        "payment_method": "QR",
        "channel": "ONLINE",
        "provider": "TEST",
        "status": "REJECTED",
    },
    {
        "code": "PAY-SEED-0004",
        "source_type": "ORDER",
        "source_code": "ORD-SEED-0004",
        "payment_method": "TRANSFER",
        "channel": "ONLINE",
        "provider": "TEST",
        "status": "APPROVED",
    },
    {
        "code": "PAY-SEED-0005",
        "source_type": "ORDER",
        "source_code": "ORD-SEED-0005",
        "payment_method": "CARD",
        "channel": "ONLINE",
        "provider": "TEST",
        "status": "FAILED",
    },

    # =====================================================
    # VENTAS PRESENCIALES
    # =====================================================
    {
        "code": "PAY-SEED-0006",
        "source_type": "SALE",
        "source_code": "VTA-SEED-0001",
        "payment_method": "CASH",
        "channel": "CASH_DESK",
        "provider": None,
        "status": "APPROVED",
    },
    {
        "code": "PAY-SEED-0007",
        "source_type": "SALE",
        "source_code": "VTA-SEED-0002",
        "payment_method": "QR",
        "channel": "CASH_DESK",
        "provider": "TEST",
        "status": "APPROVED",
    },
    {
        "code": "PAY-SEED-0008",
        "source_type": "SALE",
        "source_code": "VTA-SEED-0003",
        "payment_method": "CARD",
        "channel": "CASH_DESK",
        "provider": "TEST",
        "status": "REJECTED",
    },
]


def _money(value) -> Decimal:
    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01")
    )


def _get_inventory(
    db: Session,
    *,
    branch_id: int,
    product_variant_id: int,
) -> Inventory:

    inventory = db.scalar(
        select(Inventory)
        .where(
            Inventory.branch_id == branch_id,
            Inventory.product_variant_id
            == product_variant_id,
            Inventory.is_active.is_(True),
        )
    )

    if inventory is None:
        raise RuntimeError(
            "No existe inventario para "
            f"branch_id={branch_id}, "
            f"variant_id={product_variant_id}."
        )

    return inventory


def _movement_exists(
    db: Session,
    *,
    reference_type: str,
    reference_id: int,
    inventory_id: int,
) -> bool:

    movement = db.scalar(
        select(InventoryMovement)
        .where(
            InventoryMovement.inventory_id
            == inventory_id,
            InventoryMovement.movement_type
            == "SALE",
            InventoryMovement.reference_type
            == reference_type,
            InventoryMovement.reference_id
            == reference_id,
        )
    )

    return movement is not None


def _create_sale_movement(
    db: Session,
    *,
    inventory: Inventory,
    quantity: int,
    reference_type: str,
    reference_id: int,
    reference_code: str,
    user_id: int | None,
) -> None:

    # =====================================================
    # PROTEGER CONTRA DOBLE DESCUENTO
    # =====================================================

    if _movement_exists(
        db,
        reference_type=reference_type,
        reference_id=reference_id,
        inventory_id=inventory.id,
    ):
        return

    available = (
        inventory.stock_quantity
        - inventory.reserved_quantity
    )

    if available < quantity:
        raise RuntimeError(
            f"Inventario {inventory.id} sin "
            f"stock disponible suficiente. "
            f"Disponible={available}, "
            f"solicitado={quantity}."
        )

    stock_before = inventory.stock_quantity
    stock_after = stock_before - quantity

    reserved_before = inventory.reserved_quantity
    reserved_after = inventory.reserved_quantity

    inventory.stock_quantity = stock_after

    movement = InventoryMovement(
        inventory_id=inventory.id,
        movement_type="SALE",
        quantity=quantity,

        stock_before=stock_before,
        stock_after=stock_after,

        reserved_before=reserved_before,
        reserved_after=reserved_after,

        supplier_id=None,
        user_id=user_id,
        unit_cost=None,

        reference_type=reference_type,
        reference_id=reference_id,
        reference_code=reference_code,

        reason="Venta confirmada mediante pago aprobado.",
        notes="Movimiento generado por seed de pagos.",
    )

    db.add(
        movement
    )


def _process_order_payment(
    db: Session,
    *,
    scenario: dict,
) -> Payment:

    order = db.scalar(
        select(Order)
        .where(
            Order.order_code
            == scenario["source_code"]
        )
    )

    if order is None:
        raise RuntimeError(
            f"No existe la orden "
            f"{scenario['source_code']}."
        )

    payment = Payment(
        payment_code=scenario["code"],
        order_id=order.id,
        sale_id=None,
        user_id=order.customer_id,

        payment_method=scenario[
            "payment_method"
        ],
        channel=scenario["channel"],
        provider=scenario["provider"],

        amount=_money(
            order.total_amount
        ),
        currency="BOB",

        status=scenario["status"],

        external_transaction_id=(
            f"TX-{scenario['code']}"
        ),
        external_reference=(
            order.order_code
        ),

        failure_reason=(
            "Pago rechazado en entorno de prueba."
            if scenario["status"]
            in {"REJECTED", "FAILED"}
            else None
        ),

        paid_at=(
            datetime.now(
                timezone.utc
            )
            if scenario["status"] == "APPROVED"
            else None
        ),
    )

    db.add(
        payment
    )

    db.flush()

    # =====================================================
    # PAGO APROBADO
    # =====================================================

    if scenario["status"] == "APPROVED":

        items = list(
            db.scalars(
                select(OrderItem)
                .where(
                    OrderItem.order_id
                    == order.id
                )
            ).all()
        )

        if not items:
            raise RuntimeError(
                f"La orden {order.order_code} "
                "no tiene items."
            )

        for item in items:

            inventory = _get_inventory(
                db,
                branch_id=order.branch_id,
                product_variant_id=(
                    item.product_variant_id
                ),
            )

            _create_sale_movement(
                db,
                inventory=inventory,
                quantity=item.quantity,
                reference_type="ORDER",
                reference_id=order.id,
                reference_code=order.order_code,
                user_id=order.customer_id,
            )

        order.status = "PAID"

    elif scenario["status"] in {
        "REJECTED",
        "FAILED",
    }:
        order.status = "PAYMENT_FAILED"

    return payment


def _process_sale_payment(
    db: Session,
    *,
    scenario: dict,
) -> Payment:

    sale = db.scalar(
        select(Sale)
        .where(
            Sale.sale_code
            == scenario["source_code"]
        )
    )

    if sale is None:
        raise RuntimeError(
            f"No existe la venta "
            f"{scenario['source_code']}."
        )

    payment = Payment(
        payment_code=scenario["code"],

        order_id=None,
        sale_id=sale.id,

        user_id=(
            sale.customer_id
            if sale.customer_id is not None
            else sale.cashier_id
        ),

        payment_method=scenario[
            "payment_method"
        ],

        channel=scenario["channel"],
        provider=scenario["provider"],

        amount=_money(
            sale.total_amount
        ),

        currency="BOB",

        status=scenario["status"],

        external_transaction_id=(
            f"TX-{scenario['code']}"
        ),

        external_reference=(
            sale.sale_code
        ),

        failure_reason=(
            "Pago rechazado en entorno de prueba."
            if scenario["status"]
            in {"REJECTED", "FAILED"}
            else None
        ),

        paid_at=(
            datetime.now(
                timezone.utc
            )
            if scenario["status"] == "APPROVED"
            else None
        ),
    )

    db.add(
        payment
    )

    db.flush()

    # =====================================================
    # PAGO APROBADO
    # =====================================================

    if scenario["status"] == "APPROVED":

        items = list(
            db.scalars(
                select(SaleItem)
                .where(
                    SaleItem.sale_id
                    == sale.id
                )
            ).all()
        )

        if not items:
            raise RuntimeError(
                f"La venta {sale.sale_code} "
                "no tiene items."
            )

        for item in items:

            inventory = _get_inventory(
                db,
                branch_id=sale.branch_id,
                product_variant_id=(
                    item.product_variant_id
                ),
            )

            _create_sale_movement(
                db,
                inventory=inventory,
                quantity=item.quantity,
                reference_type="SALE",
                reference_id=sale.id,
                reference_code=sale.sale_code,
                user_id=sale.cashier_id,
            )

        sale.status = "PAID"

    # Si es rechazado dejamos la venta PENDING.
    # Puede intentarse pagar nuevamente después.

    return payment


def seed_payments(
    db: Session,
) -> None:

    print(
        "🌱 Seed pagos..."
    )

    created = 0
    existing = 0

    for scenario in PAYMENT_SCENARIOS:

        # =================================================
        # IDEMPOTENCIA
        # =================================================

        payment = db.scalar(
            select(Payment)
            .where(
                Payment.payment_code
                == scenario["code"]
            )
        )

        if payment is not None:
            existing += 1
            continue

        if scenario["source_type"] == "ORDER":

            _process_order_payment(
                db,
                scenario=scenario,
            )

        elif scenario["source_type"] == "SALE":

            _process_sale_payment(
                db,
                scenario=scenario,
            )

        else:
            raise RuntimeError(
                "Tipo de origen de pago "
                "no reconocido."
            )

        created += 1

    db.flush()

    print(
        "✅ Pagos listos: "
        f"{created} creados, "
        f"{existing} ya existentes."
    )


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================

if __name__ == "__main__":

    from app.database.session import SessionLocal
    from app.database.seeds.seed_orders import (
        seed_orders,
    )
    from app.database.seeds.seed_sales import (
        seed_sales,
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

        db.commit()

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()