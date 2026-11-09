"""Cobertura de períodos SaaS confirmados, sin alterar pagos históricos."""
from datetime import datetime, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.subscription_payment import SubscriptionPayment
from app.models.tenant_subscription import TenantSubscription


def _utc(value: datetime) -> datetime:
    return value if value.tzinfo else value.replace(tzinfo=timezone.utc)


def paid_coverage(db: Session, subscription: TenantSubscription, now: datetime) -> tuple[datetime, datetime] | None:
    """Retorna el intervalo continuo pagado que cubre `now` para el plan vigente.

    No suma períodos futuros separados por una brecha ni pagos pendientes.
    """
    if subscription.status != 'ACTIVE':
        return None
    periods = db.execute(
        select(SubscriptionPayment.period_starts_at, SubscriptionPayment.period_expires_at)
        .where(SubscriptionPayment.subscription_id == subscription.id,
               SubscriptionPayment.plan_id == subscription.plan_id,
               SubscriptionPayment.status == 'PAID',
               SubscriptionPayment.period_starts_at.is_not(None),
               SubscriptionPayment.period_expires_at.is_not(None))
        .order_by(SubscriptionPayment.period_starts_at)
    ).all()
    intervals = sorted(((_utc(s), _utc(e)) for s, e in periods if s and e and _utc(e) > _utc(s)), key=lambda x: x[0])
    merged: list[tuple[datetime, datetime]] = []
    for start, end in intervals:
        if merged and start <= merged[-1][1]:
            merged[-1] = (merged[-1][0], max(merged[-1][1], end))
        else:
            merged.append((start, end))
    now = _utc(now)
    for start, end in merged:
        if start <= now < end:
            return (start, end)
    return None


def subscription_valid_now(db: Session, subscription: TenantSubscription, now: datetime) -> bool:
    """Da soporte a contratos históricos sin pagos asociados solo con vigencia válida."""
    if subscription.status != 'ACTIVE':
        return False
    coverage = paid_coverage(db, subscription, now)
    if coverage:
        return True
    # Solo contratos legados sin pagos confirmados: evita otorgar acceso a períodos
    # futuros o con brechas cuando ya hay registros históricos pagados.
    paid_exists = db.scalar(select(SubscriptionPayment.id).where(
        SubscriptionPayment.subscription_id == subscription.id,
        SubscriptionPayment.status == 'PAID').limit(1))
    return bool(not paid_exists and subscription.starts_at and subscription.expires_at
                and _utc(subscription.starts_at) <= _utc(now) < _utc(subscription.expires_at))
