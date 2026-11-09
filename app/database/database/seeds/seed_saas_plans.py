"""Seed seguro e idempotente para los planes y suscripciones SaaS de demostración.

Uso:
  python -m app.database.seeds.seed_saas_plans --plan
  python -m app.database.seeds.seed_saas_plans --confirm
  python -m app.database.seeds.seed_saas_plans --verify

Nunca borra datos ni modifica planes/suscripciones que ya existen.
"""
from __future__ import annotations

import argparse
from decimal import Decimal

from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from app.database.seeds.seed_demo_config import EXPECTED_DATABASE
from app.database.session import SessionLocal
from app.models.branch import Branch
from app.models.subscription_plan import SubscriptionPlan
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.models.user import User

EXPECTED_REVISION = 'a46e2b00plans'

# Planes ajustados al Examen Parcial 2: Básico <= 2 sucursales, Profesional <= 10.
# Límites de personal y precios son decisiones del prototipo; no los fija la docente.
PLAN_SPECS = (
    dict(code='basico', name='Básico', description='Plan de inicio para un comercio pequeño.',
         monthly_price=Decimal('99.00'), currency='BOB', max_branches=2, max_staff=5,
         features=['catalog', 'inventory', 'sales', 'reservations', 'offline_sync', 'advanced_reports']),
    dict(code='profesional', name='Profesional', description='Plan para empresas con varias sucursales.',
         monthly_price=Decimal('249.00'), currency='BOB', max_branches=10, max_staff=25,
         features=['catalog', 'inventory', 'sales', 'reservations', 'offline_sync', 'advanced_reports', 'ai_reports']),
    dict(code='empresarial', name='Empresarial', description='Plan de demostración para cadenas comerciales.',
         monthly_price=Decimal('599.00'), currency='BOB', max_branches=50, max_staff=250,
         features=['catalog', 'inventory', 'sales', 'reservations', 'offline_sync', 'advanced_reports', 'ai_reports']),
)
TENANT_ASSIGNMENTS = {'fashionstore': 'empresarial', 'urban-style-demo': 'profesional'}


def verify_environment(db: Session) -> None:
    database = db.scalar(text('SELECT current_database()'))
    if database != EXPECTED_DATABASE:
        raise RuntimeError(f'Base inesperada: {database!r}; se esperaba {EXPECTED_DATABASE!r}')
    revisions = db.execute(text('SELECT version_num FROM alembic_version')).scalars().all()
    if revisions != [EXPECTED_REVISION]:
        raise RuntimeError(f'Migración inesperada: {revisions!r}; ejecuta/verifica Alembic antes')


def count_staff(db: Session, tenant_id: int) -> int:
    # Cuenta usuarios con rol de empleado/admin, excluyendo clientes y proveedores.
    from app.models.role import Role
    return int(db.scalar(select(func.count(User.id)).join(Role, User.role_id == Role.id)
                         .where(User.tenant_id == tenant_id,
                                Role.name.in_(['TENANT_ADMIN', 'ENCARGADO_SUCURSAL', 'CAJERO']))) or 0)


def current_state(db: Session) -> None:
    for spec in PLAN_SPECS:
        plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == spec['code']))
        print(f"PLAN {spec['code']}: " + (f"existe (id={plan.id})" if plan else 'pendiente'))
    for slug, code in TENANT_ASSIGNMENTS.items():
        tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
        if tenant is None:
            print(f'TENANT {slug}: NO EXISTE (se requiere seed de tenants)')
            continue
        subscription = db.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id))
        current = db.get(SubscriptionPlan, subscription.plan_id) if subscription else None
        branches = int(db.scalar(select(func.count(Branch.id)).where(Branch.tenant_id == tenant.id)) or 0)
        staff = count_staff(db, tenant.id)
        print(f'TENANT {slug}: {branches} sucursales, {staff} empleados, '
              f'suscripción={current.code if current else "pendiente"}, objetivo={code}')


def seed(db: Session) -> None:
    tenants = {}
    for slug in TENANT_ASSIGNMENTS:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
        if tenant is None:
            raise RuntimeError(f'No existe el tenant {slug!r}; no se realizarán cambios')
        tenants[slug] = tenant

    plans = {}
    for spec in PLAN_SPECS:
        existing = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == spec['code']))
        if existing is not None:
            # No alterar planes preexistentes, aunque difieran de la propuesta.
            plans[spec['code']] = existing
            print(f"PLAN existente {spec['code']} (sin cambios)")
        else:
            created = SubscriptionPlan(**spec, is_active=True)
            db.add(created)
            db.flush()
            plans[spec['code']] = created
            print(f"PLAN creado {spec['code']}")

    for slug, plan_code in TENANT_ASSIGNMENTS.items():
        tenant = tenants[slug]
        existing = db.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant.id))
        if existing is not None:
            print(f'SUSCRIPCIÓN existente de {slug}: se conserva sin cambios')
            continue
        plan = plans[plan_code]
        branches = int(db.scalar(select(func.count(Branch.id)).where(Branch.tenant_id == tenant.id)) or 0)
        staff = count_staff(db, tenant.id)
        if not plan.is_active or (plan.max_branches is not None and branches > plan.max_branches) or (plan.max_staff is not None and staff > plan.max_staff):
            raise RuntimeError(f'El plan {plan.code} no cubre el estado actual de {slug}: {branches} sucursales y {staff} empleados')
        db.add(TenantSubscription(tenant_id=tenant.id, plan_id=plan.id, status='ACTIVE'))
        print(f'SUSCRIPCIÓN creada: {slug} -> {plan.code}')


def main() -> None:
    parser = argparse.ArgumentParser(description='Planes y suscripciones SaaS: seguro, sin borrar datos')
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument('--plan', action='store_true', help='Previsualizar sin escribir')
    action.add_argument('--confirm', action='store_true', help='Crear registros faltantes')
    action.add_argument('--verify', action='store_true', help='Comprobar registros actuales')
    args = parser.parse_args()
    import app.models  # registrar las clases ORM
    with SessionLocal() as db:
        verify_environment(db)
        if args.confirm:
            try:
                seed(db)
                db.commit()
                print('OK: transacción confirmada; no se eliminó ni sobrescribió información existente.')
            except Exception:
                db.rollback()
                raise
        current_state(db)


if __name__ == '__main__':
    main()
