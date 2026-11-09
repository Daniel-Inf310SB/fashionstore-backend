"""Pruebas de la política comercial de devoluciones sin PostgreSQL ni Stripe."""
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from app.schemas.return_request import ReturnEligibilityOut
from app.services.return_service import return_policy_for_order, RETURN_WINDOW_DAYS

NOW = datetime(2026, 11, 6, 15, 0, tzinfo=timezone.utc)


def order(status="COMPLETED", delivery_type="PICKUP", completed_at=None, delivered_at=None):
    return SimpleNamespace(status=status, delivery_type=delivery_type,
                           completed_at=completed_at, delivered_at=delivered_at)


def test_pickup_within_seven_days():
    p = return_policy_for_order(order(completed_at=NOW - timedelta(days=6)), NOW)
    assert p["eligible"] is True
    assert p["return_deadline"] == NOW + timedelta(days=1)
    assert p["return_window_days"] == RETURN_WINDOW_DAYS == 7


def test_exact_seven_day_limit_is_expired():
    assert not return_policy_for_order(order(completed_at=NOW - timedelta(days=7)), NOW)["eligible"]


def test_pickup_not_collected_yet():
    assert not return_policy_for_order(order(status="READY_FOR_PICKUP"), NOW)["eligible"]


def test_old_order_without_delivery_date_is_not_guessed():
    p = return_policy_for_order(order(completed_at=None), NOW)
    assert not p["eligible"]
    assert p["return_deadline"] is None


def test_shipping_uses_delivery_not_completion_date():
    p = return_policy_for_order(order(status="DELIVERED", delivery_type="DELIVERY",
        delivered_at=NOW-timedelta(days=2)), NOW)
    assert p["eligible"]


def test_flutter_schema_contains_deadline():
    p = ReturnEligibilityOut.model_validate({
        "order_id": 1, "order_code": "A", "order_status": "COMPLETED",
        "can_request": True, "reason": None, "items": [],
        "delivered_at": NOW.isoformat(),
        "return_deadline": (NOW+timedelta(days=7)).isoformat(),
        "return_window_days": 7,
    })
    assert p.return_deadline is not None
