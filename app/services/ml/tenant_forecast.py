"""Pronóstico académico aislado por tenant. No crea ni modifica registros.

Las ventas de seeders siguen siendo sintéticas aun cuando vivan en PostgreSQL.
No habilitar como pronóstico comercial sin validar contra ventas reales futuras.
"""
from datetime import date, datetime, timedelta, timezone
from math import isfinite

import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.sale import Sale

MIN_SPAN_DAYS = 90
MIN_ACTIVE_DAYS = 20
HOLDOUT_DAYS = 28


def _features(day_index: int, day: date) -> list[float]:
    """Solo variables conocidas antes del día futuro: evita fuga de datos."""
    weekday = day.weekday()
    return [float(day_index), float(weekday), float(weekday >= 5),
            float(day.month), float(day.day),
            float(np.sin(2 * np.pi * weekday / 7)),
            float(np.cos(2 * np.pi * weekday / 7))]


def evaluate_and_forecast(daily_amounts: dict[date, float], *,
                          today: date, horizon: int = 7) -> dict:
    """Evaluación temporal holdout, baseline 7 días, horizontes 7/30.

    daily_amounts son ingresos DIARIOS de ventas pagadas. No se entrena
    con fechas posteriores a today. Permite ceros y no extrapola negativos.
    """
    if horizon not in (7, 30):
        raise ValueError('horizon debe ser 7 o 30')
    clean = {day: float(value) for day, value in daily_amounts.items()
             if isinstance(day, date) and day <= today and isfinite(float(value))
             and float(value) >= 0}
    active = [day for day, v in clean.items() if v > 0]
    note = ('Datos del sistema de demostración: pueden incluir operaciones sembradas. '
            'Pronóstico académico, no validación comercial con ventas reales.')
    base = {'available': False, 'mode': 'ACADEMIC', 'horizon_days': horizon,
            'disclaimer': note}
    if not active:
        return {**base, 'reason': 'No hay ventas pagadas para entrenar.'}
    first = min(clean)
    span = (today - first).days + 1
    if span < MIN_SPAN_DAYS or len(active) < MIN_ACTIVE_DAYS:
        return {**base, 'reason': 'Historial académico insuficiente: se requieren al menos 90 días de antigüedad y 20 días con ventas.',
                'history_days': span, 'active_days': len(active)}
    dates = [first + timedelta(days=i) for i in range(span)]
    y = np.asarray([clean.get(d, 0.0) for d in dates], dtype=float)
    X = np.asarray([_features(i, d) for i, d in enumerate(dates)], dtype=float)
    cut = len(dates) - HOLDOUT_DAYS
    train_x, test_x = X[:cut], X[cut:]
    train_y, test_y = y[:cut], y[cut:]
    if np.count_nonzero(train_y) < MIN_ACTIVE_DAYS // 2:
        return {**base, 'reason': 'No hay suficientes ventas antes del período de evaluación.'}
    def model():
        return RandomForestRegressor(n_estimators=80, random_state=2026,
                                     min_samples_leaf=3, n_jobs=1)
    fitted = model().fit(train_x, train_y)
    predicted_holdout = np.maximum(0, fitted.predict(test_x))
    baseline_holdout = np.asarray([float(y[max(0, i-7):i].mean()) for i in range(cut, len(y))])
    mae = float(np.abs(test_y - predicted_holdout).mean())
    baseline_mae = float(np.abs(test_y - baseline_holdout).mean())
    rmse = float(np.sqrt(np.square(test_y - predicted_holdout).mean()))
    # Reentrenar con TODO el historial solo después de evaluar con holdout.
    final = model().fit(X, y)
    future_dates = [today + timedelta(days=i) for i in range(1, horizon + 1)]
    future_x = np.asarray([_features(span + i, d) for i, d in enumerate(future_dates)])
    values = np.maximum(0, final.predict(future_x))
    return {**base, 'available': True, 'data_source': 'TENANT_PAID_SALES',
            'history_days': span, 'active_days': len(active),
            'evaluation': {'holdout_days': HOLDOUT_DAYS, 'mae_bob': round(mae, 2),
                           'rmse_bob': round(rmse, 2),
                           'baseline_mae_bob': round(baseline_mae, 2),
                           'beats_baseline': bool(mae < baseline_mae)},
            'forecast': [{'date': d.isoformat(), 'amount_bob': round(float(v), 2)}
                         for d, v in zip(future_dates, values)],
            'total_forecast_bob': round(float(values.sum()), 2)}


def tenant_forecast(db: Session, tenant_id: int, horizon: int = 7,
                    today: date | None = None) -> dict:
    """El tenant_id viene de la sesión, no de parámetros del cliente."""
    today = today or datetime.now(timezone.utc).date()
    rows = (db.query(func.date(Sale.created_at), func.sum(Sale.total_amount))
            .join(Branch, Sale.branch_id == Branch.id)
            .filter(Sale.tenant_id == tenant_id, Branch.tenant_id == tenant_id,
                    Sale.status == 'PAID', Sale.created_at < datetime.combine(today + timedelta(days=1), datetime.min.time()))
            .group_by(func.date(Sale.created_at)).all())
    daily = {}
    for day, amount in rows:
        parsed = date.fromisoformat(day) if isinstance(day, str) else day
        daily[parsed] = float(amount or 0)
    return {**evaluate_and_forecast(daily, today=today, horizon=horizon),
            'tenant_id': tenant_id}
