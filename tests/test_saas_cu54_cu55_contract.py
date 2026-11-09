"""CU54–CU55: pruebas de contrato aisladas; nunca escriben en PostgreSQL.
Ejecutar: python -m pytest tests/test_saas_cu54_cu55_contract.py -q
"""
import ast
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException
from pydantic import ValidationError
from app.schemas.subscriptions import PlanUpdate, PlanCreate
from app.models.subscription_plan import SubscriptionPlan
from app.models.tenant_subscription import TenantSubscription

SOURCE = Path(__file__).resolve().parents[1] / 'app/api/routes/platform_subscriptions.py'
TREE = ast.parse(SOURCE.read_text(encoding='utf-8'))

def isolate(name, namespace):
    fn = next(n for n in TREE.body if isinstance(n, ast.FunctionDef) and n.name == name)
    fn.decorator_list = []
    exec(compile(ast.Module(body=[fn], type_ignores=[]), str(SOURCE), 'exec'), namespace)
    return namespace[name]


def _commit(db):
    db.commit()

update_plan = isolate('update_plan', {
    'SubscriptionPlan': SubscriptionPlan, 'PlanUpdate': PlanUpdate,
    'Session': object, 'Depends': lambda x: None, 'get_db': lambda: None,
    'HTTPException': HTTPException, 'commit': _commit,
})
is_paid_active = isolate('is_paid_active', {'TenantSubscription': TenantSubscription, 'datetime': datetime})
effective_status = isolate('effective_status', {'TenantSubscription': TenantSubscription, 'datetime': datetime})


def test_cu54_editar_precio_cupos_y_funciones():
    plan = SimpleNamespace(id=8, name='Básico', monthly_price=Decimal('99'), max_branches=2, max_staff=5, features=['catalog'])
    db = MagicMock()
    db.get.return_value = plan
    db.refresh.side_effect = lambda _: None
    result = update_plan(8, PlanUpdate(monthly_price=Decimal('109.00'), max_branches=3, max_staff=6, features=['catalog', 'sales']), db)
    assert result.monthly_price == Decimal('109.00')
    assert result.max_branches == 3 and result.max_staff == 6
    assert result.features == ['catalog', 'sales']
    assert result.name == 'Básico'
    db.commit.assert_called_once()


def test_cu54_edicion_parcial_no_sobrescribe_otros_campos():
    plan = SimpleNamespace(id=1, name='Básico', monthly_price=Decimal('99'), features=['catalog'], max_staff=5)
    db = MagicMock(); db.get.return_value = plan
    update_plan(1, PlanUpdate(name='Básico actualizado'), db)
    assert plan.name == 'Básico actualizado'
    assert plan.monthly_price == Decimal('99')
    assert plan.features == ['catalog']


def test_cu54_no_editar_plan_inexistente():
    db = MagicMock(); db.get.return_value = None
    with pytest.raises(HTTPException) as err:
        update_plan(9999, PlanUpdate(name='Nuevo nombre'), db)
    assert err.value.status_code == 404
    db.commit.assert_not_called()


@pytest.mark.parametrize('payload', [
    {'monthly_price': Decimal('-1')},
    {'max_staff': 0},
    {'max_branches': 0},
    {'name': 'X'},
])
def test_cu54_rechaza_datos_invalidos(payload):
    with pytest.raises(ValidationError):
        PlanUpdate(**payload)


@pytest.mark.parametrize('payload', [{'features': None}, {'monthly_price': None}, {'is_active': None}, {'name': None}])
def test_cu54_no_admite_nulos_en_campos_requeridos(payload):
    plan = SimpleNamespace(id=1, name='Básico', monthly_price=Decimal('99'), features=['catalog'], is_active=True)
    db = MagicMock(); db.get.return_value = plan
    with pytest.raises(HTTPException) as err:
        update_plan(1, PlanUpdate(**payload), db)
    assert err.value.status_code == 422
    db.commit.assert_not_called()


def test_cu55_activa_pagada_y_vigente():
    now = datetime.now(timezone.utc)
    sub = SimpleNamespace(status='ACTIVE', expires_at=now+timedelta(days=2), price_snapshot=Decimal('99.00'))
    assert is_paid_active(sub, now)
    assert effective_status(sub, now) == 'ACTIVE'


def test_cu55_vencimiento_solo_es_estado_efectivo():
    now = datetime.now(timezone.utc)
    sub = SimpleNamespace(status='ACTIVE', expires_at=now-timedelta(seconds=1), price_snapshot=Decimal('99'))
    assert not is_paid_active(sub, now)
    assert effective_status(sub, now) == 'EXPIRED'
    assert sub.status == 'ACTIVE'  # no mutación por consulta


@pytest.mark.parametrize('status', ['SUSPENDED', 'CANCELLED', 'PENDING_PAYMENT'])
def test_cu55_suspension_cancelacion_o_impago_no_cuentan_como_activo(status):
    now = datetime.now(timezone.utc)
    sub = SimpleNamespace(status=status, expires_at=now+timedelta(days=20), price_snapshot=Decimal('99'))
    assert not is_paid_active(sub, now)
    assert effective_status(sub, now) == status


def test_cu54_precio_cero_permitido_para_planes_gratuitos():
    model = PlanCreate(code='demo', name='Demo', monthly_price=Decimal('0'), features=[])
    assert model.monthly_price == 0
