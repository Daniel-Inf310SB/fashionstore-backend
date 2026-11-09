"""Pruebas aisladas del alcance de reportes inteligentes; sin escribir en PostgreSQL."""
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from app.services.ai.context_service import AIContextService


def admin(tenant_id=3):
    return SimpleNamespace(tenant_id=tenant_id, role=SimpleNamespace(name='TENANT_ADMIN'), id=126)


def test_administrador_sin_empresa_rechazado():
    with pytest.raises(PermissionError, match='empresa'):
        AIContextService.resolve_report_branch(
            MagicMock(), current_user=admin(None), requested_branch_id=None,
        )


def test_administrador_puede_pedir_todas_sus_sucursales():
    assert AIContextService.resolve_report_branch(
        MagicMock(), current_user=admin(), requested_branch_id=None,
    ) is None


def test_sucursal_ajena_no_se_puede_seleccionar():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(LookupError, match='no existe en tu empresa'):
        AIContextService.resolve_report_branch(
            db, current_user=admin(), requested_branch_id=31,
        )
    assert db.query.return_value.filter.called


def test_sucursal_propia_autorizada():
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = SimpleNamespace(id=59, tenant_id=3)
    assert AIContextService.resolve_report_branch(
        db, current_user=admin(), requested_branch_id=59,
    ) == 59
