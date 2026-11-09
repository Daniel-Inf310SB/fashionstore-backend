"""Pruebas aisladas del Desafío VI: no conectan a PostgreSQL ni escriben datos reales.
Ejecutar desde la raíz del backend: python -m pytest tests/test_saas_limits.py -v
"""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from app.models.branch import Branch
from app.models.subscription_plan import SubscriptionPlan
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.services.branch_service import BranchService
from app.schemas.branch import BranchCreate
# Cargamos la funcion real sin importar todo el router (auth/Google).
# Esto mantiene estas pruebas unitarias independientes de integraciones externas.
import ast
import inspect
from pathlib import Path
from sqlalchemy import select, func
from app.models.user import User
from app.models.role import Role

_router_path = Path(__file__).resolve().parents[1] / "app" / "api" / "routes" / "platform_subscriptions.py"
if not _router_path.exists():
    _router_path = Path.cwd() / "app" / "api" / "routes" / "platform_subscriptions.py"
_tree = ast.parse(_router_path.read_text(encoding="utf-8"))
_node = next(n for n in _tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_plan_limits")
_namespace = {"Session": object, "SubscriptionPlan": SubscriptionPlan,
              "select": select, "func": func, "Branch": Branch, "User": User,
              "Role": Role, "HTTPException": HTTPException,
              "STAFF_ROLES": ("TENANT_ADMIN", "ENCARGADO_SUCURSAL", "CAJERO", "ADMINISTRADOR")}
exec(compile(ast.Module(body=[_node], type_ignores=[]), str(_router_path), "exec"), _namespace)
validate_plan_limits = _namespace["validate_plan_limits"]
from app.services.subscription_coverage import subscription_valid_now


def _subscription_db(*, max_branches: int, active_count: int, valid: bool = True):
    """Simula exactamente las consultas ORM de BranchService.create_branch."""
    tenant = SimpleNamespace(id=3, is_active=True)
    subscription = SimpleNamespace(status="ACTIVE", plan_id=42)
    plan = SimpleNamespace(is_active=True, max_branches=max_branches)
    db = MagicMock()

    def model_query(model):
        query = MagicMock()
        if model is Tenant:
            query.filter.return_value.with_for_update.return_value.one_or_none.return_value = tenant
        elif model is TenantSubscription:
            query.filter.return_value.one_or_none.return_value = subscription
        elif model is SubscriptionPlan:
            query.filter.return_value.one_or_none.return_value = plan
        elif model is Branch:
            query.filter.return_value.count.return_value = active_count
        else:
            raise AssertionError(f"Consulta inesperada: {model}")
        return query

    db.query.side_effect = model_query
    return db, valid


@pytest.mark.parametrize("plan_limit,existing", [(2, 0), (2, 1), (10, 9)])
def test_sucursal_dentro_limite_permitida(plan_limit, existing):
    db, valid = _subscription_db(max_branches=plan_limit, active_count=existing)
    payload = BranchCreate(name="Sucursal de prueba", address="Dirección de prueba", city_id=1)
    # Interceptamos la ejecución justo después del control de límites: sin escrituras.
    with patch("app.services.branch_service.subscription_valid_now", return_value=valid), \
         patch.object(BranchService, "_get_valid_city", side_effect=RuntimeError("LIMITE_VALIDADO")):
        with pytest.raises(RuntimeError, match="LIMITE_VALIDADO"):
            BranchService.create_branch(db=db, payload=payload, user_id=126, tenant_id=3)
    db.add.assert_not_called()
    db.commit.assert_not_called()


@pytest.mark.parametrize("plan_limit,existing", [(2, 2), (2, 3), (10, 10), (10, 11)])
def test_sucursal_fuera_limite_bloqueada(plan_limit, existing):
    db, valid = _subscription_db(max_branches=plan_limit, active_count=existing)
    payload = BranchCreate(name="Sucursal de prueba", address="Dirección de prueba", city_id=1)
    with patch("app.services.branch_service.subscription_valid_now", return_value=valid):
        with pytest.raises(ValueError, match=f"máximo {plan_limit} sucursal"):
            BranchService.create_branch(db=db, payload=payload, user_id=126, tenant_id=3)
    db.add.assert_not_called()
    db.commit.assert_not_called()


def test_sucursal_rechazada_si_suscripcion_vencida():
    db, _ = _subscription_db(max_branches=2, active_count=0)
    payload = BranchCreate(name="Sucursal de prueba", address="Dirección de prueba", city_id=1)
    with patch("app.services.branch_service.subscription_valid_now", return_value=False):
        with pytest.raises(ValueError, match="suscripción no cubre"):
            BranchService.create_branch(db=db, payload=payload, user_id=126, tenant_id=3)
    db.add.assert_not_called()


@pytest.mark.parametrize("branches,cap,should_block", [(2, 2, False), (3, 2, True), (10, 10, False), (11, 10, True)])
def test_cambio_plan_valida_sucursales(branches, cap, should_block):
    db = MagicMock()
    db.scalar.side_effect = [branches, 1]  # cantidad de sucursales, luego empleados
    plan = SimpleNamespace(max_branches=cap, max_staff=20)
    if should_block:
        with pytest.raises(HTTPException) as exc:
            validate_plan_limits(db, tenant_id=3, plan=plan)
        assert exc.value.status_code == 409
    else:
        validate_plan_limits(db, tenant_id=3, plan=plan)
    db.commit.assert_not_called()


def test_suscripcion_legada_vigente_y_vencida():
    """Contrato sin pagos históricos: vigencia por starts_at/expires_at."""
    db = MagicMock()
    db.execute.return_value.all.return_value = []
    db.scalar.return_value = None
    now = datetime.now(timezone.utc)
    sub = SimpleNamespace(id=5, plan_id=2, status="ACTIVE", starts_at=now-timedelta(days=3), expires_at=now+timedelta(days=2))
    assert subscription_valid_now(db, sub, now)
    sub.expires_at = now - timedelta(seconds=1)
    assert not subscription_valid_now(db, sub, now)
    sub.status = "CANCELED"
    assert not subscription_valid_now(db, sub, now)
