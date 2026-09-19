from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.seeds.seed_demo_config import (
    ACTIVE_CARTS,
    ABANDONED_CARTS,
    ORDERS_TOTAL,
    RESERVATIONS_TOTAL,
    SALES_TOTAL,
    SEED_UNTIL,
    SEED_YEAR,
)
from app.database.seeds.seed_customers import seed_customers
from app.models.branch import Branch
from app.models.cart_item import CartItem
from app.models.employee_branch import EmployeeBranch
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.receipt import Receipt
from app.models.receipt_item import ReceiptItem
from app.models.reservation import Reservation
from app.models.reservation_item import ReservationItem
from app.models.role import Role
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.shopping_cart import ShoppingCart
from app.models.user import User

MONEY = Decimal("0.01")


def _money(value) -> Decimal:
    return Decimal(str(value)).quantize(MONEY)


def _product_price(variant: ProductVariant) -> Decimal:
    return _money(variant.product.base_price + (variant.additional_price or Decimal("0.00")))


def _seed_customers(db: Session) -> list[User]:
    seed_customers(db)
    role = db.scalar(select(Role).where(Role.name == "CLIENTE"))
    return list(db.scalars(select(User).where(User.role_id == role.id, User.email.like("cliente%@fashionstore.com")).order_by(User.id)).all())


def _staffed_branches(db: Session) -> tuple[list[Branch], dict[int, list[User]]]:
    cashier_role = db.scalar(select(Role).where(Role.name == "CAJERO"))
    if cashier_role is None:
        raise RuntimeError("No existe rol CAJERO.")
    rows = db.execute(
        select(Branch, User)
        .join(EmployeeBranch, EmployeeBranch.branch_id == Branch.id)
        .join(User, User.id == EmployeeBranch.user_id)
        .where(EmployeeBranch.is_active.is_(True), User.role_id == cashier_role.id, Branch.is_active.is_(True))
        .order_by(Branch.id, User.id)
    ).all()
    by_branch: dict[int, list[User]] = defaultdict(list)
    branches: dict[int, Branch] = {}
    for branch, user in rows:
        branches[branch.id] = branch
        by_branch[branch.id].append(user)
    if not branches:
        raise RuntimeError("No hay sucursales con cajeros activos. Ejecuta seed_users y seed_locations.")
    return list(branches.values()), dict(by_branch)


def _inventory_map(db: Session, branches: list[Branch]) -> dict[int, list[Inventory]]:
    ids = [b.id for b in branches]
    inventories = list(db.scalars(
        select(Inventory)
        .where(Inventory.branch_id.in_(ids), Inventory.is_active.is_(True))
        .order_by(Inventory.branch_id, Inventory.id)
    ).all())
    by_branch: dict[int, list[Inventory]] = defaultdict(list)
    for inv in inventories:
        if inv.product_variant is None:
            continue
        by_branch[inv.branch_id].append(inv)
    for branch in branches:
        if len(by_branch[branch.id]) < 8:
            raise RuntimeError(f"La sucursal {branch.name} no tiene inventario suficiente para el seed comercial.")
    return dict(by_branch)


def _available(inv: Inventory) -> int:
    return int(inv.stock_quantity) - int(inv.reserved_quantity)


def _select_items(inventories: list[Inventory], seed: int, count: int, max_qty: int = 2) -> list[tuple[Inventory, int]]:
    usable = [x for x in inventories if _available(x) >= max_qty + 2]
    if len(usable) < count:
        usable = [x for x in inventories if _available(x) >= 1]
    if len(usable) < count:
        raise RuntimeError("Inventario insuficiente para generar transacciones coherentes.")
    chosen: list[tuple[Inventory, int]] = []
    used = set()
    cursor = seed * 7 + 3
    while len(chosen) < count:
        inv = usable[cursor % len(usable)]
        cursor += 11
        if inv.product_variant_id in used:
            continue
        qty = 1 + ((seed + len(chosen)) % max_qty)
        qty = min(qty, max(1, _available(inv)))
        chosen.append((inv, qty))
        used.add(inv.product_variant_id)
    return chosen


def _movement_exists(db: Session, code: str) -> bool:
    return db.scalar(select(InventoryMovement.id).where(InventoryMovement.reference_code == code)) is not None


def _decrease_stock(db: Session, inv: Inventory, qty: int, *, user_id: int | None, reference_type: str, reference_id: int, reference_code: str, at: datetime, reason: str) -> None:
    if qty <= 0 or _available(inv) < qty:
        raise RuntimeError(f"Stock insuficiente en inventory={inv.id} para {reference_code}.")
    if _movement_exists(db, reference_code):
        return
    before = int(inv.stock_quantity)
    reserved = int(inv.reserved_quantity)
    after = before - qty
    db.add(InventoryMovement(
        inventory_id=inv.id, movement_type="SALE", quantity=qty,
        stock_before=before, stock_after=after,
        reserved_before=reserved, reserved_after=reserved,
        supplier_id=None, user_id=user_id, unit_cost=None,
        reference_type=reference_type, reference_id=reference_id,
        reference_code=reference_code, reason=reason,
        notes="Movimiento generado por seed_demo_commerce.", created_at=at,
    ))
    inv.stock_quantity = after


def _reserve_stock(db: Session, inv: Inventory, qty: int, *, reference_id: int, reference_code: str, at: datetime) -> None:
    if qty <= 0 or _available(inv) < qty:
        raise RuntimeError(f"Stock insuficiente para reserva {reference_code}.")
    if _movement_exists(db, reference_code):
        return
    stock = int(inv.stock_quantity)
    before = int(inv.reserved_quantity)
    after = before + qty
    db.add(InventoryMovement(
        inventory_id=inv.id, movement_type="RESERVE", quantity=qty,
        stock_before=stock, stock_after=stock,
        reserved_before=before, reserved_after=after,
        supplier_id=None, user_id=None, unit_cost=None,
        reference_type="RESERVATION", reference_id=reference_id,
        reference_code=reference_code, reason="Stock reservado para cliente.",
        notes="Reserva activa generada por seed_demo_commerce.", created_at=at,
    ))
    inv.reserved_quantity = after


def _build_sale(db: Session, *, code: str, branch: Branch, cashier: User, customer: User | None, inventories: list[Inventory], at: datetime, seed: int, status: str) -> Sale:
    existing = db.scalar(select(Sale).where(Sale.sale_code == code))
    if existing is not None:
        return existing
    items = _select_items(inventories, seed, 1 + seed % 3)
    subtotal = sum((_product_price(inv.product_variant) * qty for inv, qty in items), Decimal("0.00"))
    discount = _money(min(Decimal("25.00"), subtotal * Decimal("0.05"))) if seed % 7 == 0 else Decimal("0.00")
    total = _money(subtotal - discount)
    sale = Sale(sale_code=code, branch_id=branch.id, cashier_id=cashier.id, customer_id=customer.id if customer else None, status=status, subtotal=_money(subtotal), discount_amount=discount, total_amount=total, created_at=at, updated_at=at)
    db.add(sale); db.flush()
    for idx, (inv, qty) in enumerate(items, 1):
        price = _product_price(inv.product_variant)
        db.add(SaleItem(sale_id=sale.id, product_variant_id=inv.product_variant_id, quantity=qty, unit_price=price, subtotal=_money(price * qty), created_at=at))
        if status == "PAID":
            _decrease_stock(db, inv, qty, user_id=cashier.id, reference_type="SALE", reference_id=sale.id, reference_code=f"SEED-SALE-{sale.id}-{idx}", at=at, reason=f"Venta presencial {code}.")
    return sale


def _payment_and_receipt_for_sale(db: Session, sale: Sale, at: datetime, method: str, sequence: int) -> None:
    if sale.status != "PAID":
        return
    pcode = f"PAY-SALE-{sale.sale_code}"
    payment = db.scalar(select(Payment).where(Payment.payment_code == pcode))
    if payment is None:
        provider = "CAJA" if method == "CASH" else ("RedEnlace" if method == "CARD" else "SimpleQR")
        payment = Payment(payment_code=pcode, order_id=None, sale_id=sale.id, user_id=sale.customer_id, payment_method=method, channel="CASH_DESK", provider=provider, amount=sale.total_amount, currency="BOB", status="APPROVED", external_transaction_id=f"TX-SALE-{sequence:06d}", external_reference=sale.sale_code, paid_at=at, created_at=at, updated_at=at)
        db.add(payment); db.flush()
    rnumber = f"REC-{sale.sale_code}"
    if db.scalar(select(Receipt.id).where(Receipt.receipt_number == rnumber)) is not None:
        return
    customer = sale.customer
    receipt = Receipt(receipt_number=rnumber, receipt_type="IN_STORE_SALE", order_id=None, sale_id=sale.id, customer_name=(f"{customer.first_name} {customer.last_name or ''}".strip() if customer else "Consumidor final"), customer_email=customer.email if customer else None, customer_document=customer.document_number if customer else None, subtotal=sale.subtotal, discount_amount=sale.discount_amount, total_amount=sale.total_amount, payment_method=method, currency="BOB", pdf_url=None, email_status="SENT" if customer else "NOT_REQUESTED", emailed_at=at + timedelta(minutes=2) if customer else None, issued_at=at + timedelta(minutes=1), created_at=at + timedelta(minutes=1))
    db.add(receipt); db.flush()
    for item in sale.items:
        variant = item.product_variant
        db.add(ReceiptItem(receipt_id=receipt.id, product_name=variant.product.name, sku=variant.sku, size_name=variant.size.name, color_name=variant.color.name, quantity=item.quantity, unit_price=item.unit_price, subtotal=item.subtotal, created_at=at + timedelta(minutes=1)))


def _seed_sales(db: Session, branches: list[Branch], cashiers: dict[int, list[User]], inventory: dict[int, list[Inventory]], customers: list[User]) -> int:
    print(f"🌱 Ventas presenciales históricas 2026: {SALES_TOTAL}...")
    methods = ["CASH", "QR", "CARD"]
    count = 0

    for i in range(SALES_TOTAL):
        branch = branches[i % len(branches)]
        branch_cashiers = cashiers[branch.id]
        month = 1 + (i % SEED_UNTIL.month)
        max_day = SEED_UNTIL.day if month == SEED_UNTIL.month else 28
        day = 1 + ((i * 7 + branch.id) % max_day)
        at = datetime(SEED_YEAR, month, day, 9 + (i % 10), (i * 13) % 60, tzinfo=timezone.utc)
        code = f"VTA-{SEED_YEAR}-{i + 1:04d}"
        seed = 10000 + i

        if i % 17 == 0:
            status = "CANCELLED"
        elif i % 13 == 0:
            status = "PENDING"
        else:
            status = "PAID"

        customer = None if i % 5 == 0 else customers[i % len(customers)]
        cashier = branch_cashiers[i % len(branch_cashiers)]
        sale = _build_sale(
            db, code=code, branch=branch, cashier=cashier, customer=customer,
            inventories=inventory[branch.id], at=at, seed=seed, status=status,
        )
        if sale.status == "PAID":
            _payment_and_receipt_for_sale(db, sale, at, methods[i % len(methods)], i + 1)
        count += 1

    db.flush()
    print(f"✅ Ventas seed procesadas: {count}.")
    return count

def _build_order(db: Session, *, code: str, branch: Branch, customer: User, inventories: list[Inventory], at: datetime, seed: int, status: str) -> Order:
    existing = db.scalar(select(Order).where(Order.order_code == code))
    if existing is not None:
        return existing
    items = _select_items(inventories, seed, 1 + seed % 3)
    subtotal = sum((_product_price(inv.product_variant) * qty for inv, qty in items), Decimal("0.00"))
    discount = Decimal("15.00") if seed % 9 == 0 and subtotal > Decimal("50") else Decimal("0.00")
    order = Order(order_code=code, customer_id=customer.id, branch_id=branch.id, status=status, subtotal=_money(subtotal), discount_amount=_money(discount), total_amount=_money(subtotal-discount), created_at=at, updated_at=at)
    db.add(order); db.flush()
    for idx, (inv, qty) in enumerate(items, 1):
        price = _product_price(inv.product_variant)
        db.add(OrderItem(order_id=order.id, product_variant_id=inv.product_variant_id, quantity=qty, unit_price=price, subtotal=_money(price*qty), created_at=at))
        if status in {"PAID", "PREPARING", "READY_FOR_PICKUP", "SHIPPED", "DELIVERED", "COMPLETED"}:
            _decrease_stock(db, inv, qty, user_id=customer.id, reference_type="ORDER", reference_id=order.id, reference_code=f"SEED-ORDER-{order.id}-{idx}", at=at, reason=f"Compra digital {code}.")
    return order


def _payment_and_receipt_for_order(db: Session, order: Order, at: datetime, method: str, sequence: int) -> None:
    approved = order.status in {"PAID", "PREPARING", "READY_FOR_PICKUP", "SHIPPED", "DELIVERED", "COMPLETED"}
    pcode = f"PAY-ORDER-{order.order_code}"
    payment = db.scalar(select(Payment).where(Payment.payment_code == pcode))
    if payment is None:
        status = "APPROVED" if approved else ("FAILED" if order.status == "PAYMENT_FAILED" else "PENDING")
        payment = Payment(payment_code=pcode, order_id=order.id, sale_id=None, user_id=order.customer_id, payment_method=method, channel="ONLINE", provider="PagoSeguro Bolivia", amount=order.total_amount, currency="BOB", status=status, external_transaction_id=f"TX-ORD-{sequence:06d}" if approved else None, external_reference=order.order_code, failure_reason="Pago rechazado por entidad emisora." if status == "FAILED" else None, paid_at=at if approved else None, created_at=at, updated_at=at)
        db.add(payment); db.flush()
    if not approved:
        return
    rnumber = f"REC-{order.order_code}"
    if db.scalar(select(Receipt.id).where(Receipt.receipt_number == rnumber)) is not None:
        return
    customer = order.customer
    receipt = Receipt(receipt_number=rnumber, receipt_type="ONLINE_PURCHASE", order_id=order.id, sale_id=None, customer_name=f"{customer.first_name} {customer.last_name or ''}".strip(), customer_email=customer.email, customer_document=customer.document_number, subtotal=order.subtotal, discount_amount=order.discount_amount, total_amount=order.total_amount, payment_method=method, currency="BOB", pdf_url=None, email_status="SENT", emailed_at=at + timedelta(minutes=3), issued_at=at + timedelta(minutes=2), created_at=at + timedelta(minutes=2))
    db.add(receipt); db.flush()
    for item in order.items:
        variant = item.product_variant
        db.add(ReceiptItem(receipt_id=receipt.id, product_name=variant.product.name, sku=variant.sku, size_name=variant.size.name, color_name=variant.color.name, quantity=item.quantity, unit_price=item.unit_price, subtotal=item.subtotal, created_at=at + timedelta(minutes=2)))


def _seed_orders(db: Session, branches: list[Branch], inventory: dict[int, list[Inventory]], customers: list[User]) -> int:
    print(f"🌱 Compras digitales históricas 2026: {ORDERS_TOTAL}...")
    methods = ["QR", "CARD", "TRANSFER"]
    statuses = [
        "COMPLETED", "DELIVERED", "SHIPPED", "PREPARING",
        "PAID", "PAYMENT_FAILED", "PENDING_PAYMENT",
    ]
    count = 0

    for i in range(ORDERS_TOTAL):
        branch = branches[(i * 5) % len(branches)]
        month = 1 + ((i * 2) % SEED_UNTIL.month)
        max_day = SEED_UNTIL.day if month == SEED_UNTIL.month else 28
        day = 1 + ((i * 9 + branch.id) % max_day)
        at = datetime(SEED_YEAR, month, day, 12 + (i % 8), (i * 11) % 60, tzinfo=timezone.utc)
        code = f"ORD-{SEED_YEAR}-{i + 1:04d}"
        seed = 30000 + i
        status = statuses[i % len(statuses)]
        customer = customers[(i * 3) % len(customers)]
        order = _build_order(
            db, code=code, branch=branch, customer=customer,
            inventories=inventory[branch.id], at=at, seed=seed, status=status,
        )
        _payment_and_receipt_for_order(db, order, at, methods[i % len(methods)], i + 1)
        count += 1

    db.flush()
    print(f"✅ Órdenes seed procesadas: {count}.")
    return count

def _seed_reservations(db: Session, branches: list[Branch], inventory: dict[int, list[Inventory]], customers: list[User]) -> int:
    print(f"🌱 Reservas históricas y actuales: {RESERVATIONS_TOTAL}...")
    statuses = ["PENDING", "CONFIRMED", "PREPARING", "READY", "ATTENDED", "COMPLETED", "CANCELLED", "EXPIRED"]
    count = 0

    for i in range(RESERVATIONS_TOTAL):
        branch = branches[i % len(branches)]
        seed = 50000 + i
        code = f"RSV-{SEED_YEAR}-{i + 1:04d}"
        if db.scalar(select(Reservation.id).where(Reservation.reservation_code == code)) is not None:
            count += 1
            continue

        month = 6 + (i % 4)
        max_day = SEED_UNTIL.day if month == SEED_UNTIL.month else 28
        if month > SEED_UNTIL.month:
            month = SEED_UNTIL.month
        day = 1 + ((i * 5 + branch.id) % (SEED_UNTIL.day if month == SEED_UNTIL.month else 28))
        at = datetime(SEED_YEAR, month, day, 10 + (i % 8), (i * 7) % 60, tzinfo=timezone.utc)
        status = statuses[i % len(statuses)]
        reservation = Reservation(
            reservation_code=code, customer_id=customers[i % len(customers)].id, branch_id=branch.id,
            status=status, notes="Reserva demo FashionStore 2026.", expires_at=at + timedelta(days=3),
            prepared_at=at + timedelta(hours=4) if status in {"PREPARING", "READY", "ATTENDED", "COMPLETED"} else None,
            attended_at=at + timedelta(days=1) if status in {"ATTENDED", "COMPLETED"} else None,
            completed_at=at + timedelta(days=1, hours=1) if status == "COMPLETED" else None,
            cancelled_at=at + timedelta(hours=6) if status == "CANCELLED" else None,
            created_at=at, updated_at=at,
        )
        db.add(reservation)
        db.flush()

        items = _select_items(inventory[branch.id], seed, 1 + (i % 2), max_qty=1)
        for idx, (inv, qty) in enumerate(items, 1):
            item_status = "PENDING"
            if status in {"CONFIRMED", "PREPARING", "READY"}:
                item_status = "RESERVED"
            elif status in {"ATTENDED", "COMPLETED"}:
                item_status = "CONSUMED"
            elif status in {"CANCELLED", "EXPIRED"}:
                item_status = "RELEASED"

            db.add(ReservationItem(
                reservation_id=reservation.id, product_variant_id=inv.product_variant_id,
                quantity=qty, unit_price=_product_price(inv.product_variant),
                status=item_status, created_at=at,
            ))

            if item_status == "RESERVED":
                _reserve_stock(db, inv, qty, reference_id=reservation.id, reference_code=f"SEED-RSV-{reservation.id}-{idx}", at=at)
            elif item_status == "CONSUMED":
                _decrease_stock(db, inv, qty, user_id=None, reference_type="RESERVATION", reference_id=reservation.id, reference_code=f"SEED-RSV-CONSUME-{reservation.id}-{idx}", at=at + timedelta(days=1), reason=f"Reserva atendida {code}.")
        count += 1

    db.flush()
    print(f"✅ Reservas seed procesadas: {count}.")
    return count

def _seed_carts(db: Session, branches: list[Branch], inventory: dict[int, list[Inventory]], customers: list[User]) -> int:
    print("🌱 Carritos activos y abandonados...")
    target = ACTIVE_CARTS + ABANDONED_CARTS
    created = 0
    # Un carrito seed por cliente como máximo para mantener lectura simple.
    for i, customer in enumerate(customers[:target]):
        branch = branches[i % len(branches)]
        existing = db.scalar(select(ShoppingCart).where(ShoppingCart.customer_id == customer.id, ShoppingCart.status.in_(["ACTIVE", "ABANDONED"])))
        if existing is not None:
            continue
        status = "ACTIVE" if i < ACTIVE_CARTS else "ABANDONED"
        at = datetime(SEED_YEAR, 9, 1 + (i % 12), 9 + (i % 10), (i * 7) % 60, tzinfo=timezone.utc)
        cart = ShoppingCart(customer_id=customer.id, branch_id=branch.id, status=status, created_at=at, updated_at=at)
        db.add(cart); db.flush()
        for inv, qty in _select_items(inventory[branch.id], 70000 + i, 1 + i % 3, max_qty=2):
            db.add(CartItem(cart_id=cart.id, product_variant_id=inv.product_variant_id, quantity=qty, created_at=at, updated_at=at))
        created += 1
    db.flush(); print(f"✅ Carritos creados en esta ejecución: {created}.")
    return created


def seed_demo_commerce(db: Session) -> None:
    print(); print("=" * 72); print("FASHIONSTORE - DATASET COMERCIAL COHERENTE 2026"); print("=" * 72)
    customers = _seed_customers(db)
    branches, cashiers = _staffed_branches(db)
    inventory = _inventory_map(db, branches)
    _seed_sales(db, branches, cashiers, inventory, customers)
    _seed_orders(db, branches, inventory, customers)
    _seed_reservations(db, branches, inventory, customers)
    _seed_carts(db, branches, inventory, customers)
    db.flush()
    print("=" * 72); print("✅ DATASET COMERCIAL 2026 COMPLETADO"); print("=" * 72); print()


if __name__ == "__main__":
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        seed_demo_commerce(db); db.commit()
    except Exception:
        db.rollback(); raise
    finally:
        db.close()
