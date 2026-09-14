from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.inventory import Inventory
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User


SALE_SCENARIOS = [
    {
        "code": "VTA-SEED-0001",
        "customer_email": "cliente01@fashionstore.com",
        "quantities": [1, 2],
        "discount": Decimal("0.00"),
    },
    {
        "code": "VTA-SEED-0002",
        "customer_email": "cliente02@fashionstore.com",
        "quantities": [1, 1],
        "discount": Decimal("10.00"),
    },
    {
        "code": "VTA-SEED-0003",
        "customer_email": "cliente03@fashionstore.com",
        "quantities": [2],
        "discount": Decimal("5.00"),
    },
    {
        "code": "VTA-SEED-0004",
        "customer_email": None,
        "quantities": [1, 1],
        "discount": Decimal("0.00"),
    },
]


def _money(value) -> Decimal:
    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01")
    )


def _get_customer(
    db: Session,
    email: str | None,
) -> User | None:

    if email is None:
        return None

    customer = db.scalar(
        select(User)
        .where(
            User.email == email
        )
    )

    if customer is None:
        raise RuntimeError(
            f"No existe el cliente {email}."
        )

    return customer


def _get_cashier(
    db: Session,
) -> User:

    cashier = db.scalar(
        select(User)
        .where(
            User.email.like(
                "cajero.%@fashionstore.com"
            )
        )
        .order_by(
            User.id
        )
    )

    if cashier is None:
        raise RuntimeError(
            "No existe ningún cajero seed. "
            "Ejecuta seed_users primero."
        )

    return cashier


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

    base_price = (
        base_price
        if base_price is not None
        else Decimal("0.00")
    )

    additional_price = (
        additional_price
        if additional_price is not None
        else Decimal("0.00")
    )

    return _money(
        base_price + additional_price
    )


def _get_branch_inventories(
    db: Session,
    *,
    minimum_available: int = 5,
) -> tuple[int, list[Inventory]]:

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
                Inventory.branch_id,
                Inventory.id,
            )
        ).all()
    )

    if not inventories:
        raise RuntimeError(
            "No existe inventario suficiente "
            "para crear ventas presenciales."
        )

    by_branch: dict[int, list[Inventory]] = {}

    for inventory in inventories:
        by_branch.setdefault(
            inventory.branch_id,
            [],
        ).append(
            inventory
        )

    for branch_id, branch_inventories in by_branch.items():

        variant_ids = {
            inventory.product_variant_id
            for inventory in branch_inventories
        }

        if len(variant_ids) >= 3:
            return (
                branch_id,
                branch_inventories,
            )

    branch_id, branch_inventories = max(
        by_branch.items(),
        key=lambda item: len(item[1]),
    )

    return (
        branch_id,
        branch_inventories,
    )


def seed_sales(
    db: Session,
) -> None:

    print(
        "🌱 Seed ventas presenciales..."
    )

    cashier = _get_cashier(
        db
    )

    branch_id, inventories = (
        _get_branch_inventories(db)
    )

    created_sales = 0
    existing_sales = 0
    created_items = 0

    inventory_index = 0

    for scenario in SALE_SCENARIOS:

        # =================================================
        # IDEMPOTENCIA
        # =================================================

        existing = db.scalar(
            select(Sale)
            .where(
                Sale.sale_code
                == scenario["code"]
            )
        )

        if existing is not None:
            existing_sales += 1
            continue

        customer = _get_customer(
            db,
            scenario["customer_email"],
        )

        # =================================================
        # CREAR VENTA
        # =================================================

        sale = Sale(
            sale_code=scenario["code"],
            branch_id=branch_id,
            cashier_id=cashier.id,
            customer_id=(
                customer.id
                if customer is not None
                else None
            ),

            # Aún no existe pago.
            status="PENDING",

            subtotal=Decimal("0.00"),
            discount_amount=scenario[
                "discount"
            ],
            total_amount=Decimal("0.00"),
        )

        db.add(
            sale
        )

        db.flush()

        subtotal = Decimal("0.00")

        used_variant_ids: set[int] = set()

        # =================================================
        # ITEMS
        # =================================================

        for quantity in scenario["quantities"]:

            selected_inventory = None
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

                selected_inventory = inventory
                break

            if selected_inventory is None:
                raise RuntimeError(
                    "No se encontró inventario "
                    "suficiente para crear "
                    "SaleItem."
                )

            used_variant_ids.add(
                selected_inventory.product_variant_id
            )

            unit_price = _get_variant_price(
                db,
                selected_inventory.product_variant_id,
            )

            item_subtotal = _money(
                unit_price * quantity
            )

            item = SaleItem(
                sale_id=sale.id,
                product_variant_id=(
                    selected_inventory.product_variant_id
                ),
                quantity=quantity,
                unit_price=unit_price,
                subtotal=item_subtotal,
            )

            db.add(
                item
            )

            subtotal += item_subtotal

            created_items += 1

        subtotal = _money(
            subtotal
        )

        discount = _money(
            scenario["discount"]
        )

        if discount > subtotal:
            raise RuntimeError(
                f"El descuento de "
                f"{scenario['code']} "
                "supera el subtotal."
            )

        total = _money(
            subtotal - discount
        )

        sale.subtotal = subtotal
        sale.discount_amount = discount
        sale.total_amount = total

        created_sales += 1

    db.flush()

    print(
        "✅ Ventas presenciales listas: "
        f"{created_sales} creadas, "
        f"{existing_sales} ya existentes, "
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

        seed_sales(
            db
        )

        db.commit()

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()