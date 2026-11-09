from datetime import date, timedelta

from app.services.ml.tenant_forecast import evaluate_and_forecast


def sample():
    today = date(2026, 10, 27)
    first = today - timedelta(days=179)
    series = {first + timedelta(days=i): float(120 + 25 * (i % 7) + (i % 15))
              for i in range(180)}
    return today, series


def test_not_enough_history():
    today, values = sample()
    result = evaluate_and_forecast(dict(list(values.items())[:10]), today=today)
    assert not result['available']


def test_forecast_has_chronological_holdout_and_no_negative_values():
    today, values = sample()
    result = evaluate_and_forecast(values, today=today, horizon=7)
    assert result['available']
    assert result['evaluation']['holdout_days'] == 28
    assert len(result['forecast']) == 7
    assert result['forecast'][0]['date'] == '2026-10-28'
    assert all(x['amount_bob'] >= 0 for x in result['forecast'])
    assert result['mode'] == 'ACADEMIC'


def test_same_data_same_prediction():
    today, values = sample()
    a = evaluate_and_forecast(values, today=today, horizon=30)
    b = evaluate_and_forecast(values, today=today, horizon=30)
    assert a == b
    assert len(a['forecast']) == 30


def test_incorrect_horizon_rejected():
    today, values = sample()
    try:
        evaluate_and_forecast(values, today=today, horizon=5)
    except ValueError:
        return
    raise AssertionError('Debe rechazar horizontes no admitidos')
