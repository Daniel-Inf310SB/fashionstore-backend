"""Verificaciones estructurales sin tocar PostgreSQL."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_tenant_endpoint_has_authorization_guards():
    source = (ROOT / 'app/api/routes/ml_analytics.py').read_text(encoding='utf-8')
    assert "@router.get('/tenant'" in source
    assert "require_permission('reports.view')" in source
    assert "require_plan_feature('ai_reports')" in source
    assert 'user.tenant_id' in source


def test_real_data_is_explicitly_tenant_scoped():
    source = (ROOT / 'app/services/ml/tenant_analytics.py').read_text(encoding='utf-8')
    assert 'Sale.tenant_id == tenant_id' in source
    assert 'Branch.tenant_id == tenant_id' in source
    assert 'Product.tenant_id == tenant_id' in source
    assert "'prediction_available': False" in source
