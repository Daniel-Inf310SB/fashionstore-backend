"""CU55: pruebas aisladas sin PostgreSQL ni escritura en el negocio.
Ejecutar: python -m pytest tests/test_cu55_subscription_readonly.py -q
"""
import ast
import calendar
from datetime import datetime, timezone, timedelta
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException, Depends

SRC = Path(__file__).resolve().parents[1] / "app/api/routes/platform_subscriptions.py"
TREE = ast.parse(SRC.read_text(encoding="utf-8"))


def load_function(name, namespace):
    node = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == name)
    # Endpoint decorators only register FastAPI routes; not relevant to isolated execution.
    node.decorator_list = []
    code = compile(ast.fix_missing_locations(ast.Module(body=[node], type_ignores=[])), str(SRC), 'exec')
    namespace.setdefault("Depends", Depends)
    exec(code, namespace)
    return namespace[name]


def test_expired_get_is_read_only_without_orm_mutation():
    now = datetime.now(timezone.utc)
    sub = SimpleNamespace(status='ACTIVE', starts_at=now-timedelta(days=40), expires_at=now-timedelta(days=1))
    db = MagicMock()
    db.get.return_value = SimpleNamespace(id=17)
    db.scalar.return_value = sub
    class FakeOut:
        @classmethod
        def model_validate(cls, value):
            return SimpleNamespace(status=value.status, starts_at=value.starts_at, expires_at=value.expires_at,
                                   model_copy=lambda update: SimpleNamespace(**{
                                       'status': value.status, 'starts_at': value.starts_at, 'expires_at': value.expires_at,
                                       **update}))
    ns = {'Tenant': object(), 'TenantSubscription': MagicMock(), 'Session': object,
          'SubscriptionOut': FakeOut, 'HTTPException': HTTPException, 'select': lambda _: MagicMock(),
          'datetime': datetime, 'timezone': timezone, 'effective_status': lambda x, at: 'EXPIRED',
          'paid_coverage': lambda db, sub, at: None, 'get_db':lambda:None}
    endpoint = load_function('get_subscription', ns)
    result = endpoint(17, db)
    assert result.status == 'EXPIRED'
    assert sub.status == 'ACTIVE', 'GET no debe modificar el estado del ORM ni hacer autoflush'
    assert db.commit.call_count == 0


@pytest.mark.parametrize('year,month,day,delta,expected', [
    (2026, 1, 31, 1, (2026, 2, 28)),
    (2024, 1, 31, 1, (2024, 2, 29)),
    (2026, 11, 23, 1, (2026, 12, 23)),
    (2026, 12, 23, 2, (2027, 2, 23)),
])
def test_calendar_renewal(year, month, day, delta, expected):
    fn = load_function('_add_months', {'datetime': datetime, 'calendar': calendar})
    result = fn(datetime(year, month, day, tzinfo=timezone.utc), delta)
    assert (result.year, result.month, result.day) == expected


def test_paid_payment_confirm_retry_is_idempotent():
    sub = SimpleNamespace(id=12)
    paid = SimpleNamespace(id=90, status='PAID', subscription_id=12)
    db = MagicMock()
    db.scalar.side_effect = [sub, paid]
    Dummy = MagicMock()
    ns = {'TenantSubscription': Dummy, 'SubscriptionPayment': Dummy,
          'SubscriptionPaymentOut': object, 'Session': object, 'select': lambda _: MagicMock(),
          'get_db': lambda:None, 'require_platform_admin':lambda:None,
          'HTTPException': HTTPException, 'datetime': datetime, 'timezone': timezone}
    fn = load_function('confirm_subscription_payment', ns)
    assert fn(22, 90, db, SimpleNamespace(id=3)) is paid
    db.commit.assert_not_called()


def test_pending_plan_does_not_silently_activate_before_payment():
    now = datetime.now(timezone.utc)
    fn = load_function('is_paid_active', {'TenantSubscription': object, 'datetime': datetime})
    sub = SimpleNamespace(status='PENDING_PAYMENT', expires_at=now + timedelta(days=30), price_snapshot=99)
    assert fn(sub, now) is False
