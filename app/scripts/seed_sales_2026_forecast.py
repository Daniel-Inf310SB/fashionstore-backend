"""Ventas académicas de enero a noviembre de 2026 para el pronóstico por tenant.

No crea clientes, no modifica suscripciones y no simula cobros externos.
Solo usar en una COPIA de la base o en la base local de desarrollo, nunca en producción.

Vista previa:
  python -m app.scripts.seed_sales_2026_forecast --year 2026 --until 2026-11-07
Aplicar en fashionstore_db LOCAL (tras hacer respaldo):
  python -m app.scripts.seed_sales_2026_forecast --year 2026 --until 2026-11-07 --apply --allow-current-db --confirm DEMO_2026
"""
from __future__ import annotations

import argparse
import hashlib
import os
import random
from collections import defaultdict
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal

from sqlalchemy import select, text
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

TENANTS = ('fashionstore', 'urban-style-demo', 'technova-store')
PREFIX = 'AF26'  # 50 caracteres máximo en sale_code/payment_code.
CONFIRMATION = 'DEMO_2026'


def dates_in_year(year: int, until: date):
    """No crea ventas futuras ni anteriores al inicio del año solicitado."""
    start = date(year, 1, 1)
    finish = min(until, date(year, 12, 31))
    if finish < start:
        raise ValueError('No puedes sembrar ventas en un año todavía no iniciado')
    for n in range((finish - start).days + 1):
        yield start + timedelta(days=n)


def scheduled_sales(slug: str, year: int, until: date):
    """Una venta diaria y una segunda en fin de semana; fechas y códigos estables."""
    for day in dates_in_year(year, until):
        for seq in range(1, 3 if day.weekday() >= 5 else 2):
            code = f'{PREFIX}-{slug}-{day:%Y%m%d}-{seq:02d}'
            if len(code) > 48:  # reserva espacio para -P en payments
                raise ValueError('Código demasiado largo')
            digest = hashlib.sha256(code.encode('utf-8')).digest()
            key = int.from_bytes(digest[:8], 'big')
            rng = random.Random(key)
            hour = 10 + rng.randrange(9)
            minute = rng.randrange(60)
            when = datetime.combine(day, time(hour, minute), tzinfo=timezone.utc)
            yield code, when, key


def allow_database(url: str, *, allow_current_db: bool, confirm: str | None, apply: bool) -> None:
    """Base demo/test siempre; BD habitual únicamente local y confirmada explícitamente."""
    parsed = make_url(url)
    name = (parsed.database or '').lower()
    host = (parsed.host or '').lower()
    env = (os.getenv('APP_ENV') or os.getenv('ENVIRONMENT') or '').lower()
    if env in {'production', 'prod'}:
        raise RuntimeError('Bloqueado en entorno production/prod')
    is_demo = name.endswith('_demo') or name.endswith('_test')
    is_local = host in {'localhost', '127.0.0.1', '::1'}
    permitted_current = (name == 'fashionstore_db' and is_local and allow_current_db)
    if not (is_demo or permitted_current):
        raise RuntimeError('Usa una base _demo/_test, o fashionstore_db LOCAL con --allow-current-db')
    if apply and confirm != CONFIRMATION:
        raise RuntimeError(f'Para insertar datos académicos, añade --confirm {CONFIRMATION}')


def prepare_tenant(db, slug: str, *, year: int, until: date, apply: bool) -> dict:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
    if tenant is None:
        raise ValueError(f'Tenant no encontrado: {slug}. Ejecuta primero los seeders base.')

    # Para aplicar, bloquear inventario durante la preparación e inserción.
    inventory_stmt = (select(Inventory, Product.base_price, ProductVariant.additional_price)
        .join(Branch, Branch.id == Inventory.branch_id)
        .join(ProductVariant, ProductVariant.id == Inventory.product_variant_id)
        .join(Product, Product.id == ProductVariant.product_id)
        .where(Branch.tenant_id == tenant.id, Product.tenant_id == tenant.id,
               Branch.is_active.is_(True), Inventory.is_active.is_(True))
        .order_by(Inventory.id))
    # El FOR UPDATE debe actuar sobre la tabla inventories (no bloquear tablas de JOIN).
    if apply:
        inventory_stmt = inventory_stmt.with_for_update(of=Inventory)
    inventory_rows = db.execute(inventory_stmt).all()
    staff_rows = db.execute(
        select(EmployeeBranch.branch_id, User)
        .join(User, User.id == EmployeeBranch.user_id)
        .join(Role, Role.id == User.role_id)
        .join(Branch, Branch.id == EmployeeBranch.branch_id)
        .where(User.tenant_id == tenant.id, Branch.tenant_id == tenant.id,
               User.is_active.is_(True), EmployeeBranch.is_active.is_(True),
               Branch.is_active.is_(True), Role.name == 'CAJERO')
    ).all()
    cashiers = defaultdict(list)
    for branch_id, user in staff_rows:
        cashiers[branch_id].append(user)
    stock = {}
    inventory_by_id = {}
    prices = {}
    for inv, base_price, additional_price in inventory_rows:
        available = int(inv.stock_quantity or 0) - int(inv.reserved_quantity or 0)
        amount = Decimal(base_price) + Decimal(additional_price or 0)
        if inv.branch_id in cashiers and available > 0 and amount > 0:
            stock[inv.id] = available
            inventory_by_id[inv.id] = inv
            prices[inv.id] = amount.quantize(Decimal('0.01'))
    if not stock:
        raise ValueError(f'{slug}: sin inventario disponible y cajeros activos')

    planned = list(scheduled_sales(slug, year, until))
    existing = set(db.scalars(select(Sale.sale_code).where(
        Sale.tenant_id == tenant.id,
        Sale.sale_code.in_([c for c, _, _ in planned])
    )))
    prepared = []
    for code, when, key in planned:
        if code in existing:
            continue
        rng = random.Random(key)
        # Elegimos aleatoriamente entre inventarios con stock, sin descontar reservas.
        eligible = [inventory_id for inventory_id, available in stock.items() if available > 0]
        if not eligible:
            raise ValueError(f'{slug}: faltan existencias para {code}; no se hicieron cambios')
        inv_id = eligible[rng.randrange(len(eligible))]
        stock[inv_id] -= 1
        prepared.append((code, when, key, inv_id))
    result = {'tenant': slug, 'tenant_id': tenant.id,
              'from': f'{year}-01-01', 'until': until.isoformat(),
              'planned': len(planned), 'existing': len(existing),
              'to_create': len(prepared), 'applied': False}
    if not apply:
        return result

    # No hacemos commit aquí: el llamador confirma todas las empresas juntas.
    for code, when, key, inv_id in prepared:
        rng = random.Random(key)
        inv = inventory_by_id[inv_id]
        cashier = rng.choice(cashiers[inv.branch_id])
        price = prices[inv_id]
        sale = Sale(tenant_id=tenant.id, sale_code=code, branch_id=inv.branch_id,
                    cashier_id=cashier.id, status='PAID', subtotal=price,
                    discount_amount=Decimal('0.00'), total_amount=price,
                    created_at=when, updated_at=when)
        db.add(sale)
        db.flush()
        db.add(SaleItem(sale_id=sale.id, product_variant_id=inv.product_variant_id,
                        quantity=1, unit_price=price, subtotal=price, created_at=when))
        db.add(Payment(payment_code=f'{code}-P', sale_id=sale.id, user_id=cashier.id,
                       payment_method=rng.choice(('CASH', 'QR', 'TRANSFER')),
                       channel='CASH_DESK', provider='ACADEMIC_SEED_2026',
                       status='APPROVED', amount=price, currency='BOB',
                       paid_at=when, created_at=when, updated_at=when))
        before = int(inv.stock_quantity)
        if before <= int(inv.reserved_quantity):
            raise ValueError(f'{slug}: stock cambió durante el proceso; se revertirá todo')
        inv.stock_quantity = before - 1
        db.add(InventoryMovement(
            inventory_id=inv.id, movement_type='SALE', quantity=1,
            stock_before=before, stock_after=before - 1,
            reserved_before=inv.reserved_quantity, reserved_after=inv.reserved_quantity,
            user_id=cashier.id, reference_type='SALE', reference_id=sale.id,
            reference_code=code, reason='Venta sintética académica 2026',
            notes='Solo para pruebas del pronóstico por tenant', created_at=when))
    db.flush()
    result['applied'] = True
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--year', type=int, default=2026)
    p.add_argument('--until', type=date.fromisoformat, default=None,
                   help='Último día incluido, YYYY-MM-DD; por defecto hoy UTC')
    p.add_argument('--tenant', choices=TENANTS, action='append',
                   help='Se puede repetir; por defecto las tres empresas')
    p.add_argument('--apply', action='store_true', help='Inserta en la base de datos')
    p.add_argument('--allow-current-db', action='store_true',
                   help='Permite fashionstore_db SOLO cuando está en localhost')
    p.add_argument('--confirm', default=None, help=f'Confirmación explícita: {CONFIRMATION}')
    args = p.parse_args()
    until = min(args.until or datetime.now(timezone.utc).date(), date(args.year, 12, 31))
    if until > datetime.now(timezone.utc).date():
        p.error('No se permiten fechas futuras')
    if args.year != 2026:
        p.error('Este seeder está dedicado exclusivamente al año 2026')
    try:
        allow_database(str(engine.url), allow_current_db=args.allow_current_db,
                       confirm=args.confirm, apply=args.apply)
    except RuntimeError as exc:
        p.error(str(exc))
    # Importar todos los modelos para resolver relaciones ORM.
    import app.models  # noqa: F401
    with SessionLocal() as db:
        try:
            # Bloqueo de sesión por transacción: evita dos ejecuciones simultáneas del seeder.
            if args.apply:
                db.execute(text('SELECT pg_advisory_xact_lock(2026, 7711)'))
            reports = [prepare_tenant(db, slug, year=args.year, until=until,
                                      apply=args.apply) for slug in dict.fromkeys(args.tenant or TENANTS)]
            for report in reports:
                print(report)
            if args.apply:
                db.commit()
                print('COMMIT realizado: historial académico de 2026 insertado.')
            else:
                db.rollback()
                print('DRY RUN: no se han modificado datos. Guarda un backup antes de usar --apply.')
        except Exception:
            db.rollback()
            raise


if __name__ == '__main__':
    main()
