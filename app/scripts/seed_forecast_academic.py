"""Historial académico de ventas, exclusivamente para una base DEMO/TEST.

Uso: python -m app.scripts.seed_forecast_academic --tenant fashionstore --days 180
     python -m app.scripts.seed_forecast_academic --tenant fashionstore --days 180 --apply

La primera orden es un dry-run. Nunca ejecutar sobre datos productivos.
"""
import argparse
import random
from datetime import datetime, timedelta, time, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.engine.url import make_url

from app.database.session import SessionLocal, engine
from app.models.tenant import Tenant
from app.models.branch import Branch
from app.models.user import User
from app.models.employee_branch import EmployeeBranch
from app.models.role import Role
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.payment import Payment

PREFIX = 'ACADEMIC-FORECAST-V1'


def is_demo_database(url: str) -> bool:
    """Condición deliberadamente estricta: el nombre debe acabar en _demo o _test."""
    name = (make_url(url).database or '').lower()
    return name.endswith('_demo') or name.endswith('_test')


def plan(days: int, seed: int = 2026, anchor=None):
    if not 90 <= days <= 365:
        raise ValueError('days debe estar entre 90 y 365')
    from datetime import date
    anchor = anchor or datetime.now(timezone.utc).date()
    rng = random.Random(seed)
    for offset in range(days - 1, -1, -1):
        day = anchor - timedelta(days=offset)
        # Ventas desiguales, pero todos los días tienen al menos una.
        count = (3 if day.weekday() in (5, 6) else 2) + rng.randint(0, 2)
        for sequence in range(1, count + 1):
            code = f'{PREFIX}-{day:%Y%m%d}-{sequence:02d}'
            timestamp = datetime.combine(day, time(hour=10 + sequence % 10, minute=(sequence * 13) % 60), tzinfo=timezone.utc)
            yield code, timestamp, rng.randrange(10**9)


def seed(db, *, slug: str, days: int, apply: bool, seed_value: int = 2026) -> dict:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
    if tenant is None:
        raise ValueError(f'Tenant inexistente: {slug}')
    branches = list(db.scalars(select(Branch).where(Branch.tenant_id == tenant.id).order_by(Branch.id)))
    assigned = db.execute(select(EmployeeBranch.branch_id, User).join(User, User.id == EmployeeBranch.user_id)
        .join(Role, Role.id == User.role_id).where(User.tenant_id == tenant.id, User.is_active.is_(True),
            EmployeeBranch.is_active.is_(True), Role.name == 'CAJERO')).all()
    cashiers_by_branch = {}
    for bid, cashier in assigned:
        cashiers_by_branch.setdefault(bid, []).append(cashier)
    if not branches or not cashiers_by_branch:
        raise ValueError('La empresa requiere sucursales y cajeros asignados activos')
    invs = list(db.scalars(select(Inventory).join(Branch, Inventory.branch_id == Branch.id)
        .join(ProductVariant, Inventory.product_variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .where(Branch.tenant_id == tenant.id, Product.tenant_id == tenant.id, Inventory.is_active.is_(True))
        .order_by(Inventory.id)))
    invs = [inv for inv in invs if inv.branch_id in cashiers_by_branch]
    if not invs:
        raise ValueError('La empresa no tiene inventario con cajero asignado')
    schedule = list(plan(days, seed=seed_value))
    codes = {code for code, _, _ in schedule}
    prior = set(db.scalars(select(Sale.sale_code).where(Sale.tenant_id == tenant.id, Sale.sale_code.in_(codes))))
    # Comprobación previa sin modificar ninguna fila: suficientes unidades por inventario.
    allocated = {}
    prepared = []
    for code, timestamp, key in schedule:
        if code in prior:
            continue
        rng = random.Random(key)
        candidates = [inv for inv in invs if int(inv.stock_quantity or 0) - int(inv.reserved_quantity or 0) - allocated.get(inv.id, 0) >= 1]
        if not candidates:
            raise ValueError('Stock insuficiente en la base DEMO para todo el historial. No se realizaron cambios.')
        inv = candidates[rng.randrange(len(candidates))]
        allocated[inv.id] = allocated.get(inv.id, 0) + 1
        prepared.append((code, timestamp, inv, key))
    result = {'tenant': slug, 'tenant_id': tenant.id, 'days': days,
              'planned': len(schedule), 'existing': len(prior), 'to_create': len(prepared), 'applied': False}
    if not apply:
        return result
    # Una sola transacción. Si cualquier inserción falla, el llamador revierte todo.
    for code, timestamp, inv, key in prepared:
        rng = random.Random(key)
        branch_id = inv.branch_id
        # Datos académicos: cada venta pagada usa un empleado propio del tenant.
        branch_cashiers = cashiers_by_branch[branch_id]
        cashier = branch_cashiers[rng.randrange(len(branch_cashiers))]
        variant = db.get(ProductVariant, inv.product_variant_id)
        product = db.get(Product, variant.product_id)
        unit_price = Decimal(product.base_price) + Decimal(variant.additional_price or 0)
        if unit_price <= 0:
            raise ValueError(f'Precio no válido para variante {variant.id}')
        sale = Sale(tenant_id=tenant.id, sale_code=code, branch_id=branch_id,
                    cashier_id=cashier.id, status='PAID', subtotal=unit_price,
                    discount_amount=Decimal('0.00'), total_amount=unit_price,
                    created_at=timestamp, updated_at=timestamp)
        db.add(sale)
        db.flush()
        db.add(SaleItem(sale_id=sale.id, product_variant_id=variant.id, quantity=1,
                        unit_price=unit_price, subtotal=unit_price, created_at=timestamp))
        method = ['CASH', 'QR', 'TRANSFER'][rng.randrange(3)]
        db.add(Payment(payment_code=f'{code}-P', sale_id=sale.id,
                       user_id=cashier.id, payment_method=method,
                       channel='CASH_DESK', provider='ACADEMIC_SEED',
                       status='APPROVED', amount=unit_price, currency='BOB',
                       paid_at=timestamp, created_at=timestamp, updated_at=timestamp))
        before = int(inv.stock_quantity)
        inv.stock_quantity = before - 1
        db.add(InventoryMovement(inventory_id=inv.id, movement_type='SALE',
                    quantity=1, stock_before=before, stock_after=before - 1,
                    reserved_before=inv.reserved_quantity,
                    reserved_after=inv.reserved_quantity, user_id=cashier.id,
                    reference_type='SALE', reference_id=sale.id,
                    reference_code=code, reason='Historial académico para pronóstico'))
    db.flush()
    result['applied'] = True
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tenant', required=True, help='Slug del tenant de prueba')
    parser.add_argument('--days', type=int, default=180)
    parser.add_argument('--seed', type=int, default=2026)
    parser.add_argument('--apply', action='store_true', help='Confirmar inserciones en BD de prueba')
    args = parser.parse_args()
    if not is_demo_database(str(engine.url)):
        parser.error('BLOQUEADO: DATABASE_URL debe terminar en _demo o _test. No uses la BD habitual.')
    with SessionLocal() as db:
        try:
            result = seed(db, slug=args.tenant, days=args.days, seed_value=args.seed, apply=args.apply)
            if args.apply:
                db.commit()
            else:
                db.rollback()
            print(result)
        except Exception:
            db.rollback()
            raise


if __name__ == '__main__':
    main()
