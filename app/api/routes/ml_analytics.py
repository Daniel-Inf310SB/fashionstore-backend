"""Resultados académicos sintéticos: sin datos ni predicciones de tenants reales."""
import logging
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from app.database.session import get_db
from app.services.ml.tenant_analytics import tenant_analysis

from app.dependencies.permissions import require_permission
from app.dependencies.plan_features import require_plan_feature
from app.dependencies.tenant_context import require_tenant_user
from app.services.ml.experiment import run_demo

router = APIRouter(prefix='/analytics/ml', tags=['ML Analytics'])
logger = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def _demo_metrics():
    # Determinístico, sin DB y solo lectura; no entrenamos por cada petición.
    return run_demo(seed=2026)


@router.get('/demo', summary='Resultados académicos de ML con datos sintéticos')
def get_ml_demo(
    _tenant_user=Depends(require_tenant_user),
    _permission=Depends(require_permission('reports.view')),
    _feature=Depends(require_plan_feature('ai_reports')),
):
    try:
        return _demo_metrics()
    except Exception as exc:
        # No dejar una excepción sin manejar: con CORS en FastAPI una respuesta
        # 500 generada fuera del middleware puede parecer un fallo de CORS.
        logger.exception('Falló el cálculo del experimento ML')
        raise HTTPException(
            status_code=503,
            detail='No fue posible calcular el experimento ML. Revisa el log del backend.',
        ) from exc


@router.get('/tenant', summary='Analítica descriptiva real aislada por empresa')
def get_ml_tenant(
    days: int = 90,
    user=Depends(require_tenant_user),
    _permission=Depends(require_permission('reports.view')),
    _feature=Depends(require_plan_feature('ai_reports')),
    db=Depends(get_db),
):
    if not 7 <= days <= 365:
        raise HTTPException(status_code=422, detail='days debe estar entre 7 y 365')
    return tenant_analysis(db, user.tenant_id, days)


@router.get('/tenant/forecast', summary='Pronóstico académico de ventas pagadas por tenant')
def get_ml_tenant_forecast(
    horizon: int = 7,
    user=Depends(require_tenant_user),
    _permission=Depends(require_permission('reports.view')),
    _feature=Depends(require_plan_feature('ai_reports')),
    db=Depends(get_db),
):
    from app.services.ml.tenant_forecast import tenant_forecast
    if horizon not in (7, 30):
        raise HTTPException(status_code=422, detail='horizon debe ser 7 o 30')
    return tenant_forecast(db, user.tenant_id, horizon)
