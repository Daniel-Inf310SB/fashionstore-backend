"""Pruebas puras de calendario, códigos y barrera de seguridad del seeder."""
from datetime import date
import pytest
from app.scripts.seed_sales_2026_forecast import (
    dates_in_year, scheduled_sales, allow_database,
)


def test_year_to_date_covers_january_to_november():
    days = list(dates_in_year(2026, date(2026, 11, 7)))
    assert days[0] == date(2026, 1, 1)
    assert days[-1] == date(2026, 11, 7)
    assert len(days) == 311


def test_codes_are_unique_per_tenant_and_stable():
    f = list(scheduled_sales('fashionstore', 2026, date(2026, 11, 7)))
    t = list(scheduled_sales('technova-store', 2026, date(2026, 11, 7)))
    assert f == list(scheduled_sales('fashionstore', 2026, date(2026, 11, 7)))
    assert set(r[0] for r in f).isdisjoint(r[0] for r in t)
    assert len(set(r[0] for r in f)) == len(f)
    assert len(f) >= 311
    assert all(len(code + '-P') <= 50 for code, _, _ in f + t)


def test_production_database_is_blocked(monkeypatch):
    monkeypatch.setenv('APP_ENV', 'production')
    with pytest.raises(RuntimeError):
        allow_database('postgresql://u:p@localhost/fashionstore_demo',
                       allow_current_db=False, confirm='DEMO_2026', apply=True)


def test_current_database_needs_local_host_and_explicit_approval(monkeypatch):
    monkeypatch.delenv('APP_ENV', raising=False)
    monkeypatch.delenv('ENVIRONMENT', raising=False)
    with pytest.raises(RuntimeError):
        allow_database('postgresql://u:p@localhost/fashionstore_db',
                       allow_current_db=False, confirm='DEMO_2026', apply=True)
    with pytest.raises(RuntimeError):
        allow_database('postgresql://u:p@remote/fashionstore_db',
                       allow_current_db=True, confirm='DEMO_2026', apply=True)
    with pytest.raises(RuntimeError):
        allow_database('postgresql://u:p@localhost/fashionstore_db',
                       allow_current_db=True, confirm=None, apply=True)
    allow_database('postgresql://u:p@localhost/fashionstore_db',
                   allow_current_db=True, confirm='DEMO_2026', apply=True)
