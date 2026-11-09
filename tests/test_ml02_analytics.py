"""Pruebas independientes de PostgreSQL; autorización mediante dependencias FastAPI."""
import pytest
pytest.importorskip('numpy')
pytest.importorskip('pandas')
pytest.importorskip('sklearn')

from app.services.ml.experiment import synthetic_product_profiles, train_unsupervised
from app.api.routes.ml_analytics import _demo_metrics, get_ml_demo


def test_profiles_cover_all_synthetic_products():
    _, result = train_unsupervised(synthetic_product_profiles())
    assert len(result['profiles']) == 3
    assert sum(x['products'] for x in result['profiles']) == 120
    assert {x['relative_segment'] for x in result['profiles']} == {
        'ROTACION_BAJA', 'ROTACION_MEDIA', 'ROTACION_ALTA'
    }
    assert all(x['average_available_stock'] >= 0 for x in result['profiles'])


def test_demo_result_is_synthetic_and_reproducible():
    a = _demo_metrics()
    b = _demo_metrics()
    assert a == b
    assert a['supervised']['data_source'] == 'SYNTHETIC_DEMO'
    assert a['unsupervised']['data_source'] == 'SYNTHETIC_DEMO'


def test_endpoint_requires_permission_and_plan_dependency():
    from fastapi.routing import APIRoute
    from app.api.routes.ml_analytics import router
    routes = [r for r in router.routes if isinstance(r, APIRoute)]
    routes_by_path = {route.path: route for route in routes}
    assert {'/analytics/ml/demo', '/analytics/ml/tenant'} <= set(routes_by_path)
    # Tanto la demo sintética como la analítica real exigen usuario del tenant,
    # permiso de reportes y función ai_reports del plan contratado.
    for path in ('/analytics/ml/demo', '/analytics/ml/tenant'):
        route = routes_by_path[path]
        assert 'GET' in route.methods
        deps = route.dependant.dependencies
        names = {dep.call.__name__ for dep in deps}
        assert 'require_tenant_user' in names, path
        assert sum(name == 'dependency' for name in names) >= 1, path
        # require_permission y require_plan_feature devuelven cierres llamados
        # "dependency"; comprobamos ambas dependencias, no solo una.
        assert len([dep for dep in deps if dep.call.__name__ == 'dependency']) >= 2, path


def test_endpoint_payload_matches_cached_demo():
    assert get_ml_demo() == _demo_metrics()
