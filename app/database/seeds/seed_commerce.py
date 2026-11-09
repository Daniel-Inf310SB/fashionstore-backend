"""Bloque 5: comercio demo multi-tenant; sin llamadas a Stripe ni borrados.

Una transacción es gestionada por seed_multitenant. Códigos DEMO-B5 son
exclusivos del generador; una ejecución repetida no duplica operaciones.
"""
import os
from dotenv import load_dotenv
load_dotenv()
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import select, func

from app.core.security import hash_password
from app.models.user import User
from app.models.role import Role
from app.models.branch import Branch
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.shopping_cart import ShoppingCart
from app.models.cart_item import CartItem
from app.models.reservation import Reservation
from app.models.reservation_item import ReservationItem
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.payment import Payment
from app.models.receipt import Receipt
from app.models.receipt_item import ReceiptItem
from app.database.seeds.seed_demo_config import DEMO_TENANTS

NOW = lambda: datetime.now(timezone.utc)
PREFIX = 'DEMO-B5'


def _customer_list(db, tenant_id, slug, count, role):
    password = os.getenv('SEED_CUSTOMER_PASSWORD')
    if not password or len(password) < 12:
        raise RuntimeError('Configura SEED_CUSTOMER_PASSWORD (mínimo 12 caracteres)')
    output = []
    alias = {'fashionstore': 'fs', 'urban-style-demo': 'us', 'technova-store': 'tn'}[slug]
    for n in range(1, count + 1):
        email = f'{alias}.cliente{n:02d}@example.com'
        user = db.scalar(select(User).where(User.email == email))
        if user is None:
            user = User(email=email, username=f'{alias}_cliente_{n:02d}',
                        first_name=f'Cliente {n:02d}', last_name=slug,
                        role_id=role.id, tenant_id=tenant_id,
                        password_hash=hash_password(password), is_active=True,
                        is_verified=True, profile_completed=True)
            db.add(user)
            db.flush()
        if user.tenant_id != tenant_id or user.role_id != role.id:
            raise RuntimeError(f'Cliente con tenant/rol incorrecto: {email}')
        output.append(user)
    return output


def _receipt(db, *, code, source, customer, lines, amount, payment_method):
    prior = db.scalar(select(Receipt).where(Receipt.receipt_number == code))
    if prior is not None:
        return prior
    receipt = Receipt(receipt_number=code,
                      receipt_type='ONLINE_PURCHASE' if isinstance(source, Order) else 'IN_STORE_SALE',
                      order_id=source.id if isinstance(source, Order) else None,
                      sale_id=source.id if isinstance(source, Sale) else None,
                      customer_name=(customer.first_name + ' ' + (customer.last_name or '')).strip(),
                      customer_email=customer.email, subtotal=amount,
                      discount_amount=Decimal('0.00'), total_amount=amount,
                      payment_method=payment_method, currency='BOB',
                      email_status='NOT_REQUESTED')
    db.add(receipt)
    db.flush()
    for inv, qty, unit in lines:
        variant = inv.product_variant
        db.add(ReceiptItem(receipt_id=receipt.id, product_name=variant.product.name,
                           sku=variant.sku, quantity=qty, unit_price=unit,
                           subtotal=unit * qty))
    return receipt


def _take_stock(db, inv, qty, source_type, source_id, actor_id, ref_code):
    if inv.stock_quantity - inv.reserved_quantity < qty:
        raise RuntimeError(f'Sin stock: inventario {inv.id}, referencia {ref_code}')
    old = inv.stock_quantity
    inv.stock_quantity = old - qty
    db.add(InventoryMovement(inventory_id=inv.id, movement_type='SALE',
                             quantity=qty, stock_before=old, stock_after=inv.stock_quantity,
                             reserved_before=inv.reserved_quantity,
                             reserved_after=inv.reserved_quantity,
                             user_id=actor_id, reference_type=source_type,
                             reference_id=source_id, reference_code=ref_code,
                             reason='Venta de demostración Multi-Tenant'))


def _pay(db, *, code, order_id=None, sale_id=None, customer, method, amount):
    if db.scalar(select(Payment.id).where(Payment.payment_code == code)) is not None:
        return
    db.add(Payment(payment_code=code, order_id=order_id, sale_id=sale_id,
                   user_id=customer.id, payment_method=method,
                   channel='ONLINE' if order_id is not None else 'CASH_DESK',
                   provider='DEMO_LOCAL', amount=amount, currency='BOB',
                   status='APPROVED', paid_at=NOW()))


def _available_inventories(db, branch, tenant_id):
    rows = db.scalars(select(Inventory).join(ProductVariant,
                 Inventory.product_variant_id == ProductVariant.id).join(Product,
                 ProductVariant.product_id == Product.id).where(
                 Inventory.branch_id == branch.id, Product.tenant_id == tenant_id,
                 Inventory.is_active.is_(True),
                 Inventory.stock_quantity - Inventory.reserved_quantity >= 2
                 ).order_by(Inventory.id)).all()
    return rows


def _assert_preconditions(db, tid, spec, branches, customers):
    products = db.scalar(select(func.count(Product.id)).where(Product.tenant_id == tid))
    invs = db.scalar(select(func.count(Inventory.id)).join(Branch, Inventory.branch_id == Branch.id).where(Branch.tenant_id == tid))
    if len(branches) != spec.branches or products != spec.products or invs != spec.branches * spec.products * spec.variants_per_product:
        raise RuntimeError(f'Bloques 2-4 incompletos en {spec.slug}: sucursales {len(branches)}, productos {products}, inventarios {invs}')
    if len(customers) != spec.customers:
        raise RuntimeError('Número de clientes inesperado')


def seed_commerce(db, tenant_ids):
    role = db.scalar(select(Role).where(Role.name == 'CLIENTE'))
    cash_role = db.scalar(select(Role).where(Role.name == 'CAJERO'))
    if role is None or cash_role is None:
        raise RuntimeError('Primero ejecuta Bloque 2: faltan roles CLIENTE/CAJERO')
    reports = {}
    for spec in DEMO_TENANTS:
        tid = tenant_ids[spec.slug]
        customers = _customer_list(db, tid, spec.slug, spec.customers, role)
        branches = db.scalars(select(Branch).where(Branch.tenant_id == tid).order_by(Branch.id)).all()
        _assert_preconditions(db, tid, spec, branches, customers)
        cashiers = db.scalars(select(User).where(User.tenant_id == tid, User.role_id == cash_role.id).order_by(User.id)).all()
        if len(cashiers) != len(branches) * 2:
            raise RuntimeError(f'Cajeros incompletos en {spec.slug}')
        branch_cashiers = {}
        from app.models.employee_branch import EmployeeBranch
        for branch in branches:
            assigned = db.scalars(select(User).join(EmployeeBranch, User.id == EmployeeBranch.user_id).where(
                EmployeeBranch.branch_id == branch.id, EmployeeBranch.is_active.is_(True),
                User.role_id == cash_role.id, User.tenant_id == tid)).all()
            if len(assigned) != 2:
                raise RuntimeError(f'Sucursal {branch.id} no tiene 2 cajeros válidos')
            branch_cashiers[branch.id] = assigned
        new_sales = new_orders = new_carts = 0
        for n in range(1, spec.sales + 1):
            code = f'{PREFIX}-{tid}-S-{n:04d}'
            if db.scalar(select(Sale.id).where(Sale.sale_code == code)) is not None:
                continue
            branch = branches[(n-1) % len(branches)]
            inv_list = _available_inventories(db, branch, tid)
            if not inv_list:
                raise RuntimeError(f'No existe inventario vendible para sucursal {branch.id}')
            inv = inv_list[(n * 7) % len(inv_list)]
            customer = customers[(n-1) % len(customers)]
            cashier = branch_cashiers[branch.id][n % 2]
            unit = Decimal(inv.product_variant.product.base_price) + Decimal(inv.product_variant.additional_price)
            total = unit * 1
            sale = Sale(tenant_id=tid, sale_code=code, branch_id=branch.id,
                        cashier_id=cashier.id, customer_id=customer.id,
                        status='PAID', subtotal=total, discount_amount=0, total_amount=total)
            db.add(sale); db.flush()
            db.add(SaleItem(sale_id=sale.id, product_variant_id=inv.product_variant_id,
                            quantity=1, unit_price=unit, subtotal=total))
            _take_stock(db, inv, 1, 'SALE', sale.id, cashier.id, code)
            method = ('CASH', 'QR', 'TRANSFER')[n % 3]
            _pay(db, code=f'{code}-PAY', sale_id=sale.id, customer=customer, method=method, amount=total)
            _receipt(db, code=f'{code}-REC', source=sale, customer=customer,
                     lines=[(inv, 1, unit)], amount=total, payment_method=method)
            new_sales += 1
        # 80% de los pedidos se completan; el resto queda pendiente de pago.
        for n in range(1, spec.orders + 1):
            code = f'{PREFIX}-{tid}-O-{n:04d}'
            if db.scalar(select(Order.id).where(Order.order_code == code)) is not None:
                continue
            branch = branches[(n-1) % len(branches)]
            inv_list = _available_inventories(db, branch, tid)
            if not inv_list: raise RuntimeError('Sin existencias para pedido ' + code)
            inv = inv_list[(n * 11) % len(inv_list)]
            customer = customers[(n-1) % len(customers)]
            unit = Decimal(inv.product_variant.product.base_price) + Decimal(inv.product_variant.additional_price)
            paid = n % 5 != 0
            order = Order(tenant_id=tid, order_code=code, branch_id=branch.id,
                          customer_id=customer.id, status='COMPLETED' if paid else 'PENDING_PAYMENT',
                          subtotal=unit, discount_amount=0, total_amount=unit,
                          delivery_type='PICKUP', paid_at=NOW() if paid else None,
                          completed_at=NOW() if paid else None)
            db.add(order);db.flush()
            db.add(OrderItem(order_id=order.id, product_variant_id=inv.product_variant_id,
                             quantity=1, unit_price=unit, subtotal=unit))
            if paid:
                # El carrito histórico convertido queda unido conceptualmente
                # al pedido mediante cliente/sucursal e ítem (el esquema no tiene order.cart_id).
                historical_cart = ShoppingCart(customer_id=customer.id, branch_id=branch.id, status='CONVERTED')
                db.add(historical_cart); db.flush()
                db.add(CartItem(cart_id=historical_cart.id, product_variant_id=inv.product_variant_id, quantity=1))
                _take_stock(db, inv, 1, 'ORDER', order.id, None, code)
                _pay(db, code=f'{code}-PAY', order_id=order.id, customer=customer, method='QR', amount=unit)
                _receipt(db, code=f'{code}-REC', source=order, customer=customer,
                         lines=[(inv, 1, unit)], amount=unit, payment_method='QR')
            new_orders += 1
        # Carritos activos/abandonados. No descontar ni reservar stock.
        cart_targets = (6, 3) if spec.slug == 'fashionstore' else (2, 1)
        for status, total_count in [('ACTIVE', cart_targets[0]), ('ABANDONED', cart_targets[1])]:
            for n in range(total_count):
                customer = customers[n + (0 if status == 'ACTIVE' else cart_targets[0])]
                branch = branches[n % len(branches)]
                existing = db.scalar(select(ShoppingCart.id).where(
                    ShoppingCart.customer_id == customer.id, ShoppingCart.branch_id == branch.id,
                    ShoppingCart.status == status))
                if existing is not None: continue
                invs = _available_inventories(db, branch, tid)
                if not invs: raise RuntimeError('No hay variantes para el carrito')
                cart = ShoppingCart(customer_id=customer.id, branch_id=branch.id, status=status)
                db.add(cart);db.flush()
                db.add(CartItem(cart_id=cart.id, product_variant_id=invs[n % len(invs)].product_variant_id, quantity=1))
                new_carts += 1
        # Reservas PENDING: no alteran existencias hasta que el servicio las confirme.
        for n in range(1, (8 if spec.slug == 'fashionstore' else 2) + 1):
            code = f'{PREFIX}-{tid}-R-{n:04d}'
            if db.scalar(select(Reservation.id).where(Reservation.reservation_code == code)) is not None: continue
            branch = branches[(n-1) % len(branches)]
            available = _available_inventories(db, branch, tid)
            if not available: raise RuntimeError('Sin stock para reservar ' + code)
            inv = available[n % len(available)]
            customer = customers[(n-1) % len(customers)]
            unit = Decimal(inv.product_variant.product.base_price) + Decimal(inv.product_variant.additional_price)
            reservation = Reservation(tenant_id=tid, reservation_code=code,
                                      customer_id=customer.id, branch_id=branch.id,
                                      status='PENDING', notes='Reserva de demostración pendiente')
            db.add(reservation);db.flush()
            db.add(ReservationItem(reservation_id=reservation.id, product_variant_id=inv.product_variant_id,
                                   quantity=1, unit_price=unit, status='PENDING'))
        reports[spec.slug] = dict(customers=len(customers), sales_created=new_sales,
                                   orders_created=new_orders, carts_created=new_carts)
    db.flush()
    return reports
