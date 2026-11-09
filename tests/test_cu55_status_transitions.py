"""CU55: contratos aislados de suspensión, cancelación y reactivación."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock
import pytest
from fastapi import HTTPException
from app.schemas.subscriptions import SubscriptionAssign
import ast
from pathlib import Path
from fastapi import Depends
SOURCE = Path(__file__).resolve().parents[1] / 'app/api/routes/platform_subscriptions.py'
TREE = ast.parse(SOURCE.read_text(encoding='utf-8'))
def _extract(name, ns):
    node = next(x for x in TREE.body if isinstance(x, ast.FunctionDef) and x.name == name)
    node.decorator_list = []
    exec(compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(SOURCE), 'exec'), ns)
    return ns[name]

def commit(db): db.commit()
def validate_plan_limits(*a): pass
def subscription_valid_now_for_reactivation(*a): return True
from app.models.tenant import Tenant
from app.models.subscription_plan import SubscriptionPlan
from app.models.tenant_subscription import TenantSubscription
from sqlalchemy import select
base = dict(Session=object, Depends=Depends, get_db=lambda:None, SubscriptionOut=object,
            Tenant=Tenant, SubscriptionPlan=SubscriptionPlan, TenantSubscription=TenantSubscription,
            SubscriptionAssign=SubscriptionAssign, select=select, HTTPException=HTTPException,
            validate_plan_limits=validate_plan_limits, commit=commit, datetime=datetime, timezone=timezone,
            is_paid_active=lambda sub,now:sub.status=='ACTIVE' and sub.expires_at>now and sub.price_snapshot is not None)
assign_subscription = _extract('assign_subscription',dict(base,subscription_valid_now_for_reactivation=lambda *a:True))


def _db(status='ACTIVE', plan_id=1):
    now = datetime.now(timezone.utc)
    sub = SimpleNamespace(id=5, tenant_id=7, plan_id=plan_id, status=status,
                          starts_at=now-timedelta(days=1), expires_at=now+timedelta(days=15),
                          price_snapshot=99, pending_plan_id=None)
    plan = SimpleNamespace(id=1, is_active=True)
    tenant = SimpleNamespace(id=7)
    db = MagicMock()
    db.get.side_effect = [tenant, plan]
    db.scalar.return_value = sub
    return db, sub

@pytest.mark.parametrize('target', ['SUSPENDED', 'CANCELLED'])
def test_suspend_or_cancel_without_clearing_paid_period(monkeypatch, target):
    db, sub = _db()
    result = assign_subscription(7, SubscriptionAssign(plan_id=1, status=target), db)
    assert result.status == target
    assert sub.expires_at > datetime.now(timezone.utc)
    db.commit.assert_called_once()

@pytest.mark.parametrize('target', ['SUSPENDED', 'CANCELLED'])
def test_reactivate_only_with_confirmed_coverage(monkeypatch, target):
    db, sub = _db(target)
    result = assign_subscription(7, SubscriptionAssign(plan_id=1, status='ACTIVE'), db)
    assert result.status == 'ACTIVE'
    db.commit.assert_called_once()

@pytest.mark.parametrize('target', ['SUSPENDED', 'CANCELLED'])
def test_reactivate_expired_denied(monkeypatch, target):
    db, sub = _db(target)
    reject = _extract("assign_subscription", dict(base,subscription_valid_now_for_reactivation=lambda *a:False))
    with pytest.raises(HTTPException) as err:
        reject(7, SubscriptionAssign(plan_id=1, status='ACTIVE'), db)
    assert err.value.status_code == 409
    assert sub.status == target
    db.commit.assert_not_called()


def test_cannot_change_plan_when_suspending(monkeypatch):
    db, sub = _db(plan_id=2)
    with pytest.raises(HTTPException) as err:
        assign_subscription(7, SubscriptionAssign(plan_id=1, status='SUSPENDED'), db)
    assert err.value.status_code == 409
    db.commit.assert_not_called()


def test_reactivation_has_no_paid_coverage_when_no_confirmed_history():
    now = datetime.now(timezone.utc)
    sub = SimpleNamespace(id=5, plan_id=1, starts_at=now-timedelta(days=45),
                          expires_at=now-timedelta(days=10), price_snapshot=99)
    db = MagicMock(); db.scalar.return_value = None
    helper = _extract('subscription_valid_now_for_reactivation', dict(Session=object, TenantSubscription=object,
                SubscriptionPayment=__import__('app.models.subscription_payment',fromlist=['SubscriptionPayment']).SubscriptionPayment,
                select=select, datetime=datetime, timezone=timezone))
    assert helper(db, sub, now) is False
