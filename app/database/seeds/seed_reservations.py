from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.reservation import Reservation
from app.models.reservation_item import ReservationItem
from app.models.user import User


SEED_RESERVATION_PREFIX = "RSV-SEED"


def _money(
    value,
) -> Decimal:

    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01")
    )


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


def _get_available_inventory(
    db: Session,
    *,
    excluded_inventory_ids: set[int],
    minimum_available: int = 5,
) -> Inventory:

    inventories = list(
        db.scalars(
            select(Inventory)
            .where(
                Inventory.is_active.is_(True),
                Inventory.stock_quantity
                - Inventory.reserved_quantity
                >= minimum_available,
            )
            .order_by(
                Inventory.id
            )
        ).all()
    )

    for inventory in inventories:

        if inventory.id not in excluded_inventory_ids:
            return inventory

    raise RuntimeError(
        "No se encontró inventario suficiente "
        "para generar las reservas seed."
    )


def _get_variant_price(
    db: Session,
    variant_id: int,
) -> Decimal:

    row = db.execute(
        select(
            Product.base_price,
            ProductVariant.additional_price,
        )
        .join(
            ProductVariant,
            ProductVariant.product_id
            == Product.id,
        )
        .where(
            ProductVariant.id == variant_id
        )
    ).first()

    if row is None:
        raise RuntimeError(
            f"No existe la variante {variant_id}."
        )

    base_price, additional_price = row

    return _money(
        base_price
        + additional_price
    )


def _create_inventory_movement(
    db: Session,
    *,
    inventory: Inventory,
    movement_type: str,
    quantity: int,
    reserved_before: int,
    reserved_after: int,
    customer_id: int,
    reservation: Reservation,
    reason: str,
) -> None:

    movement = InventoryMovement(
        inventory_id=inventory.id,
        movement_type=movement_type,
        quantity=quantity,

        stock_before=inventory.stock_quantity,
        stock_after=inventory.stock_quantity,

        reserved_before=reserved_before,
        reserved_after=reserved_after,

        supplier_id=None,
        user_id=customer_id,
        unit_cost=None,

        reference_type="RESERVATION",
        reference_id=reservation.id,
        reference_code=reservation.reservation_code,

        reason=reason,
        notes="Movimiento generado por seed de reservas.",
    )

    db.add(
        movement
    )


def _reserve_item(
    db: Session,
    *,
    reservation: Reservation,
    inventory: Inventory,
    quantity: int,
) -> ReservationItem:

    available_quantity = (
        inventory.stock_quantity
        - inventory.reserved_quantity
    )

    if available_quantity < quantity:
        raise RuntimeError(
            f"Inventario {inventory.id} "
            f"sin disponibilidad suficiente."
        )

    unit_price = _get_variant_price(
        db,
        inventory.product_variant_id,
    )

    item = ReservationItem(
        reservation_id=reservation.id,
        product_variant_id=inventory.product_variant_id,
        quantity=quantity,
        unit_price=unit_price,
        status="RESERVED",
    )

    db.add(
        item
    )

    reserved_before = (
        inventory.reserved_quantity
    )

    reserved_after = (
        reserved_before
        + quantity
    )

    inventory.reserved_quantity = (
        reserved_after
    )

    _create_inventory_movement(
        db,
        inventory=inventory,
        movement_type="RESERVE",
        quantity=quantity,
        reserved_before=reserved_before,
        reserved_after=reserved_after,
        customer_id=reservation.customer_id,
        reservation=reservation,
        reason="Reserva de prendas.",
    )

    return item


def _release_item(
    db: Session,
    *,
    reservation: Reservation,
    inventory: Inventory,
    item: ReservationItem,
) -> None:

    reserved_before = (
        inventory.reserved_quantity
    )

    reserved_after = (
        reserved_before
        - item.quantity
    )

    if reserved_after < 0:
        raise RuntimeError(
            "El stock reservado no puede "
            "quedar negativo."
        )

    inventory.reserved_quantity = (
        reserved_after
    )

    item.status = "RELEASED"

    _create_inventory_movement(
        db,
        inventory=inventory,
        movement_type="RELEASE",
        quantity=item.quantity,
        reserved_before=reserved_before,
        reserved_after=reserved_after,
        customer_id=reservation.customer_id,
        reservation=reservation,
        reason="Liberación por cancelación de reserva.",
    )


def seed_reservations(
    db: Session,
) -> None:

    print(
        "🌱 Seed reservas..."
    )

    # =====================================================
    # IDEMPOTENCIA
    # =====================================================

    existing_codes = set(
        db.scalars(
            select(
                Reservation.reservation_code
            )
            .where(
                Reservation.reservation_code.like(
                    f"{SEED_RESERVATION_PREFIX}-%"
                )
            )
        ).all()
    )

    # =====================================================
    # CLIENTES
    # =====================================================

    customers = [
        _get_customer(
            db,
            "cliente01@fashionstore.com",
        ),
        _get_customer(
            db,
            "cliente02@fashionstore.com",
        ),
        _get_customer(
            db,
            "cliente03@fashionstore.com",
        ),
        _get_customer(
            db,
            "cliente04@fashionstore.com",
        ),
        _get_customer(
            db,
            "cliente05@fashionstore.com",
        ),
        _get_customer(
            db,
            "cliente06@fashionstore.com",
        ),
    ]

    # =====================================================
    # ESCENARIOS
    # =====================================================

    scenarios = [
        {
            "code": "RSV-SEED-0001",
            "customer": customers[0],
            "status": "PENDING",
            "quantity": 2,
            "cancel": False,
        },
        {
            "code": "RSV-SEED-0002",
            "customer": customers[1],
            "status": "CONFIRMED",
            "quantity": 1,
            "cancel": False,
        },
        {
            "code": "RSV-SEED-0003",
            "customer": customers[2],
            "status": "PREPARING",
            "quantity": 2,
            "cancel": False,
        },
        {
            "code": "RSV-SEED-0004",
            "customer": customers[3],
            "status": "READY",
            "quantity": 1,
            "cancel": False,
        },
        {
            "code": "RSV-SEED-0005",
            "customer": customers[4],
            "status": "ATTENDED",
            "quantity": 1,
            "cancel": False,
        },
        {
            "code": "RSV-SEED-0006",
            "customer": customers[5],
            "status": "CANCELLED",
            "quantity": 2,
            "cancel": True,
        },
    ]

    created = 0
    skipped = 0

    used_inventory_ids: set[int] = set()

    now = datetime.now(
        timezone.utc
    )

    for index, scenario in enumerate(
        scenarios,
        start=1,
    ):

        code = scenario["code"]

        if code in existing_codes:
            skipped += 1
            continue

        inventory = _get_available_inventory(
            db,
            excluded_inventory_ids=used_inventory_ids,
            minimum_available=5,
        )

        used_inventory_ids.add(
            inventory.id
        )

        branch = db.get(
            Branch,
            inventory.branch_id,
        )

        if branch is None:
            raise RuntimeError(
                f"No existe la sucursal "
                f"{inventory.branch_id}."
            )

        reservation = Reservation(
            reservation_code=code,
            customer_id=scenario[
                "customer"
            ].id,
            branch_id=branch.id,
            status=scenario["status"],
            notes=(
                "Reserva generada automáticamente "
                "para pruebas de la Iteración 2."
            ),
            expires_at=(
                now
                + timedelta(
                    days=2 + index
                )
            ),
        )

        if scenario["status"] in {
            "PREPARING",
            "READY",
            "ATTENDED",
        }:
            reservation.prepared_at = now

        if scenario["status"] == "ATTENDED":
            reservation.attended_at = now

        if scenario["status"] == "CANCELLED":
            reservation.cancelled_at = now

        db.add(
            reservation
        )

        db.flush()

        item = _reserve_item(
            db,
            reservation=reservation,
            inventory=inventory,
            quantity=scenario["quantity"],
        )

        db.flush()

        if scenario["cancel"]:

            _release_item(
                db,
                reservation=reservation,
                inventory=inventory,
                item=item,
            )

        created += 1

    db.flush()

    print(
        "✅ Reservas listas: "
        f"{created} creadas, "
        f"{skipped} ya existentes."
    )
if __name__ == "__main__":
    from app.database.session import SessionLocal
    from app.database.seeds.seed_customers import seed_customers

    db = SessionLocal()

    try:
        # Asegura que existan los clientes primero
        seed_customers(db)

        # Crea las reservas
        seed_reservations(db)

        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()