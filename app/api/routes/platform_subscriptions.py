"""Catálogo de planes y asignación de suscripciones. Solo SUPER_ADMIN."""
from datetime import datetime, timezone, timedelta
import calendar
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select, func, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.tenant_context import require_platform_admin
from app.models.tenant import Tenant
from app.models.branch import Branch
from app.models.user import User
from app.models.role import Role
from app.models.subscription_plan import SubscriptionPlan
from app.models.tenant_subscription import TenantSubscription
from app.models.subscription_payment import SubscriptionPayment
from app.services.subscription_coverage import paid_coverage, subscription_valid_now
from app.schemas.subscriptions import PlanCreate, PlanUpdate, PlanOut, SubscriptionAssign, SubscriptionOut, EntitlementOut, PaymentRequest, SubscriptionPaymentOut

router = APIRouter(prefix="/platform", tags=["Platform - Subscriptions"], dependencies=[Depends(require_platform_admin)])

def commit(db):
    try: db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(409, "Código de plan duplicado u otra restricción de datos") from exc


# Empleados de la empresa, excluyendo clientes y proveedores.
STAFF_ROLES = ("TENANT_ADMIN", "ENCARGADO_SUCURSAL", "CAJERO", "ADMINISTRADOR")

def validate_plan_limits(db: Session, tenant_id: int, plan: SubscriptionPlan) -> None:
    branches = db.scalar(select(func.count(Branch.id)).where(Branch.tenant_id == tenant_id, Branch.is_active.is_(True))) or 0
    staff = db.scalar(select(func.count(User.id)).join(Role, User.role_id == Role.id).where(
        User.tenant_id == tenant_id, User.is_active.is_(True), Role.name.in_(STAFF_ROLES))) or 0
    if plan.max_branches is not None and branches > plan.max_branches:
        raise HTTPException(409, f"La empresa tiene {branches} sucursales activas y el plan permite {plan.max_branches}")
    if plan.max_staff is not None and staff > plan.max_staff:
        raise HTTPException(409, f"La empresa tiene {staff} empleados activos y el plan permite {plan.max_staff}")

def is_paid_active(sub: TenantSubscription, now: datetime) -> bool:
    return sub.status == "ACTIVE" and sub.expires_at is not None and sub.expires_at > now and sub.price_snapshot is not None

def effective_status(sub: TenantSubscription, now: datetime) -> str:
    if sub.status == "ACTIVE" and sub.expires_at is not None and sub.expires_at <= now:
        return "EXPIRED"
    return sub.status

@router.get("/plans", response_model=list[PlanOut])
def list_plans(db: Session = Depends(get_db)):
    return db.scalars(select(SubscriptionPlan).order_by(SubscriptionPlan.id)).all()

@router.post("/plans", response_model=PlanOut, status_code=201)
def create_plan(payload: PlanCreate, db: Session = Depends(get_db)):
    plan = SubscriptionPlan(**payload.model_dump())
    db.add(plan); commit(db); db.refresh(plan); return plan

@router.patch("/plans/{plan_id}", response_model=PlanOut)
def update_plan(plan_id: int, payload: PlanUpdate, db: Session = Depends(get_db)):
    plan = db.get(SubscriptionPlan, plan_id)
    if not plan: raise HTTPException(404, "Plan no encontrado")
    values = payload.model_dump(exclude_unset=True)
    if any(v is None for k,v in values.items() if k in {'name','monthly_price','features','is_active'}):
        raise HTTPException(422, "Campo requerido no puede ser nulo")
    for key,value in values.items(): setattr(plan,key,value)
    commit(db); db.refresh(plan); return plan

@router.get("/tenants/{tenant_id}/subscription", response_model=SubscriptionOut | None)
def get_subscription(tenant_id: int, db: Session = Depends(get_db)):
    if not db.get(Tenant, tenant_id): raise HTTPException(404, "Empresa no encontrada")
    sub = db.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id))
    if sub is None:
        return None
    # Solo calcular la respuesta. Nunca mutar el modelo ORM en una ruta GET:
    # una consulta posterior puede disparar autoflush y persistir EXPIRED.
    now = datetime.now(timezone.utc)
    result = SubscriptionOut.model_validate(sub)
    changes = {"status": effective_status(sub, now)}
    coverage = paid_coverage(db, sub, now)
    if coverage:
        changes.update({"starts_at": coverage[0], "expires_at": coverage[1]})
    return result.model_copy(update=changes)


def subscription_valid_now_for_reactivation(db: Session, sub: TenantSubscription, now: datetime) -> bool:
    """Comprueba cobertura confirmada sin mutar el estado persistido."""
    paid = db.scalar(select(SubscriptionPayment.id).where(
        SubscriptionPayment.subscription_id == sub.id,
        SubscriptionPayment.status == "PAID").limit(1))
    if paid:
        # paid_coverage requiere ACTIVE, pero no se debe alterar sub.status ni por un instante.
        periods = db.execute(select(SubscriptionPayment.period_starts_at, SubscriptionPayment.period_expires_at).where(
            SubscriptionPayment.subscription_id == sub.id,
            SubscriptionPayment.plan_id == sub.plan_id,
            SubscriptionPayment.status == "PAID")).all()
        return any(start is not None and end is not None
                   and (start if start.tzinfo else start.replace(tzinfo=timezone.utc)) <= now
                   < (end if end.tzinfo else end.replace(tzinfo=timezone.utc))
                   for start, end in periods)
    return bool(sub.starts_at and sub.expires_at and sub.price_snapshot is not None
                and (sub.starts_at if sub.starts_at.tzinfo else sub.starts_at.replace(tzinfo=timezone.utc)) <= now
                < (sub.expires_at if sub.expires_at.tzinfo else sub.expires_at.replace(tzinfo=timezone.utc)))


@router.put("/tenants/{tenant_id}/subscription", response_model=SubscriptionOut)
def assign_subscription(tenant_id: int, payload: SubscriptionAssign, db: Session = Depends(get_db)):
    tenant = db.get(Tenant, tenant_id)
    if not tenant: raise HTTPException(404, "Empresa no encontrada")
    plan = db.get(SubscriptionPlan, payload.plan_id)
    if not plan: raise HTTPException(409, "Plan no disponible")
    sub = db.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id).with_for_update())
    if not plan.is_active and not (sub is not None and sub.plan_id == plan.id
                                   and "status" in payload.model_fields_set
                                   and payload.status in ("SUSPENDED", "CANCELLED")):
        raise HTTPException(409, "Plan no disponible")
    if payload.expires_at is not None:
        raise HTTPException(409, "El vencimiento se calcula al confirmar un pago")
    validate_plan_limits(db, tenant_id, plan)
    now = datetime.now(timezone.utc)
    # Las transiciones explícitas no deben confundirse con la asignación de un plan.
    # La reactivación restaura solamente cobertura pagada todavía vigente.
    explicit_status = "status" in payload.model_fields_set
    if explicit_status and payload.status in ("SUSPENDED", "CANCELLED"):
        if sub is None:
            raise HTTPException(409, "No existe una suscripción para suspender o cancelar")
        if sub.plan_id != plan.id:
            raise HTTPException(409, "No se puede cambiar de plan al suspender o cancelar")
        sub.status = payload.status
        commit(db); db.refresh(sub); return sub
    if explicit_status and payload.status == "ACTIVE" and sub is not None and sub.status in ("SUSPENDED", "CANCELLED"):
        if sub.plan_id != plan.id:
            raise HTTPException(409, "No se puede cambiar de plan al reactivar")
        if not subscription_valid_now_for_reactivation(db, sub, now):
            raise HTTPException(409, "La suscripción no tiene cobertura pagada vigente para reactivarse")
        sub.status = "ACTIVE"
        commit(db); db.refresh(sub); return sub
    if sub is None:
        sub = TenantSubscription(tenant_id=tenant_id, plan_id=plan.id, status="PENDING_PAYMENT")
        db.add(sub)
    elif is_paid_active(sub, now):
        if sub.plan_id == plan.id:
            sub.pending_plan_id = None  # Permite cancelar el cambio programado
        else:
            sub.pending_plan_id = plan.id  # No altera el período vigente pagado
    else:
        # Un período sin pago vigente puede elegir plan, pero no se activa sin cobro.
        sub.plan_id = plan.id
        sub.pending_plan_id = None
        sub.status = "PENDING_PAYMENT"
        sub.expires_at = None
    commit(db); db.refresh(sub); return sub

@router.get("/tenants/{tenant_id}/entitlements", response_model=EntitlementOut)
def entitlements(tenant_id: int, db: Session = Depends(get_db)):
    tenant = db.get(Tenant, tenant_id)
    if not tenant: raise HTTPException(404, "Empresa no encontrada")
    sub = db.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id))
    plan = db.get(SubscriptionPlan, sub.plan_id) if sub else None
    allowed = bool(tenant.is_active and sub and sub.status == 'ACTIVE' and plan and plan.is_active and subscription_valid_now(db, sub, datetime.now(timezone.utc)))
    return EntitlementOut(tenant_id=tenant_id, subscription_status=effective_status(sub, datetime.now(timezone.utc)) if sub else None, plan_code=plan.code if plan else None, max_branches=plan.max_branches if allowed else None, max_staff=plan.max_staff if allowed else None, features=plan.features if allowed else [], allowed=allowed)


# Las operaciones de cobro NO son pagos del comercio; corresponden a la plataforma SaaS.
def _add_months(value: datetime, months: int) -> datetime:
    """Mes calendario conservando día cuando es posible (31 enero + 1 = 28 febrero)."""
    index = value.year * 12 + (value.month - 1) + months
    year, month0 = divmod(index, 12)
    month = month0 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return value.replace(year=year, month=month, day=day)


@router.get("/tenants/{tenant_id}/subscription/payments", response_model=list[SubscriptionPaymentOut])
def list_subscription_payments(tenant_id: int, db: Session = Depends(get_db)):
    if not db.get(Tenant, tenant_id):
        raise HTTPException(404, "Empresa no encontrada")
    sub = db.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id))
    if sub is None:
        return []
    return db.scalars(select(SubscriptionPayment).where(SubscriptionPayment.subscription_id == sub.id).order_by(SubscriptionPayment.id.desc())).all()


@router.post("/tenants/{tenant_id}/subscription/payments", response_model=SubscriptionPaymentOut, status_code=201)
def request_subscription_payment(tenant_id: int, payload: PaymentRequest, db: Session = Depends(get_db)):
    """Genera un pago PENDING; nunca extiende ni activa la suscripción."""
    if not db.get(Tenant, tenant_id):
        raise HTTPException(404, "Empresa no encontrada")
    plan = db.get(SubscriptionPlan, payload.plan_id)
    if plan is None or not plan.is_active:
        raise HTTPException(409, "Plan no disponible")
    sub = db.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id).with_for_update())
    if sub is None:
        raise HTTPException(409, "La empresa todavía no tiene suscripción; asígnale una primero")
    # Referencia única evita doble registro por reintentos del cliente.
    reference = payload.reference.strip()
    if not reference:
        raise HTTPException(422, "Referencia obligatoria")
    existing = db.scalar(select(SubscriptionPayment).where(SubscriptionPayment.reference == reference))
    if existing:
        if existing.subscription_id == sub.id and existing.plan_id == plan.id and existing.duration_months == payload.duration_months and existing.method == payload.method:
            return existing
        raise HTTPException(409, "Referencia ya utilizada")
    validate_plan_limits(db, tenant_id, plan)
    payment = SubscriptionPayment(
        subscription_id=sub.id, plan_id=plan.id,
        duration_months=payload.duration_months,
        amount=(Decimal(plan.monthly_price) * Decimal(payload.duration_months)).quantize(Decimal("0.01")),
        currency=plan.currency, method=payload.method, status="PENDING", reference=reference,
    )
    db.add(payment)
    commit(db)
    db.refresh(payment)
    return payment


@router.post("/tenants/{tenant_id}/subscription/payments/{payment_id}/confirm", response_model=SubscriptionPaymentOut)
def confirm_subscription_payment(tenant_id: int, payment_id: int, db: Session = Depends(get_db), admin=Depends(require_platform_admin)):
    """Confirmación manual explícita. Se debe verificar el cobro fuera de este endpoint."""
    sub = db.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id).with_for_update())
    if sub is None:
        raise HTTPException(404, "Suscripción no encontrada")
    payment = db.scalar(select(SubscriptionPayment).where(SubscriptionPayment.id == payment_id, SubscriptionPayment.subscription_id == sub.id).with_for_update())
    if payment is None:
        raise HTTPException(404, "Pago no encontrado")
    if payment.status == "PAID":
        return payment  # confirmación idempotente, no renueva dos veces
    if payment.status != "PENDING":
        raise HTTPException(409, "Solo se pueden confirmar pagos pendientes")
    plan = db.get(SubscriptionPlan, payment.plan_id)
    if plan is None:
        raise HTTPException(409, "Plan no disponible")
    validate_plan_limits(db, tenant_id, plan)
    now = datetime.now(timezone.utc)
    if is_paid_active(sub, now) and payment.plan_id != sub.plan_id:
        raise HTTPException(409, "El plan vigente ya está pagado. Confirma el cambio de plan tras su vencimiento; el pago permanece pendiente")
    # Si el plan cambia, el nuevo período empieza ahora; si se renueva el mismo,
    # no se pierden días de un período vigente.
    same_plan = sub.plan_id == payment.plan_id
    starts = sub.expires_at if same_plan and sub.status == "ACTIVE" and sub.expires_at and sub.expires_at > now else now
    expires = _add_months(starts, payment.duration_months)
    sub.plan_id = payment.plan_id
    sub.pending_plan_id = None
    # Conservar el inicio original de la cobertura al renovar el mismo plan.
    # Los períodos individuales quedan en SubscriptionPayment sin alteración.
    if not (same_plan and sub.status == "ACTIVE" and sub.expires_at and sub.expires_at > now):
        sub.starts_at = starts
    sub.expires_at = expires
    sub.status = "ACTIVE"
    sub.duration_months = payment.duration_months
    sub.price_snapshot = payment.amount
    sub.currency_snapshot = payment.currency
    payment.status = "PAID"
    payment.paid_at = now
    payment.period_starts_at = starts
    payment.period_expires_at = expires
    payment.confirmed_by_user_id = admin.id
    commit(db)
    db.refresh(payment)
    return payment
