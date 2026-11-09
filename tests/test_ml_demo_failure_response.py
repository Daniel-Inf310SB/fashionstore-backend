"""El endpoint de ML no debe convertir fallos de cálculo en excepciones 500 sin manejar."""
from unittest.mock import patch

import pytest
from fastapi import HTTPException

from app.api.routes.ml_analytics import get_ml_demo


def test_ml_demo_calculation_failure_returns_diagnostic_http_error():
    with patch('app.api.routes.ml_analytics._demo_metrics', side_effect=RuntimeError('test error')):
        with pytest.raises(HTTPException) as exc:
            get_ml_demo()
    assert exc.value.status_code == 503
    assert 'experimento ML' in exc.value.detail
