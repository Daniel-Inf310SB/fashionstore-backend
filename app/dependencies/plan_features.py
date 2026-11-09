"""Exige funcionalidades SaaS en el servidor, además de permisos RBAC."""
from datetime import datetime, timezone
from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.tenant_context import require_tenant_user
from app.models.subscription_plan import SubscriptionPlan
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.models.user import User
from app.services.subscription_coverage import subscription_valid_now


def require_plan_feature(feature: str):
    def dependency(user: User = Depends(require_tenant_user), db: Session = Depends(get_db)) -> User:
        tenant = db.get(Tenant, user.tenant_id)
        if tenant is None or not tenant.is_active:
            raise HTTPException(status_code=403, detail="La empresa está inactiva o no existe.")
        sub = db.query(TenantSubscription).filter(TenantSubscription.tenant_id == user.tenant_id).one_or_none()
        if sub is None or not subscription_valid_now(db, sub, datetime.now(timezone.utc)):
            raise HTTPException(status_code=403, detail="La empresa no tiene una suscripción vigente.")
        plan = db.get(SubscriptionPlan, sub.plan_id)
        if plan is None or not plan.is_active or feature not in (plan.features or []):
            raise HTTPException(status_code=403, detail=f"Tu plan no incluye la funcionalidad: {feature}.")
        return user
    return dependency
