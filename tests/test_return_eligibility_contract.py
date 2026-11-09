"""Offline/Flutter return contract checks, without a database or Stripe account."""
from pathlib import Path

from app.schemas.return_request import ReturnEligibilityOut, ReturnCreate
from app.services.return_service import RESERVING_STATES, remaining_return_quantities


def test_received_returns_still_consume_eligible_units():
    assert "RECEIVED" in RESERVING_STATES
    assert remaining_return_quantities({10: 3}, {10: 2}) == {10: 1}
    assert remaining_return_quantities({10: 3}, {10: 3}) == {10: 0}


def test_return_eligibility_contract_exposes_variants_and_remaining_units():
    output = ReturnEligibilityOut.model_validate({
        "order_id": 1, "order_code": "ORDER-1", "order_status": "DELIVERED",
        "can_request": True, "reason": None,
        "items": [{"order_item_id": 5, "product_variant_id": 8,
                   "purchased_quantity": 2, "already_requested_quantity": 1,
                   "available_quantity": 1, "unit_price": "100.00", "subtotal": "200.00"}],
    })
    assert output.items[0].available_quantity == 1
    assert output.items[0].product_variant_id == 8


def test_return_create_rejects_invalid_quantities():
    from pydantic import ValidationError
    import pytest
    with pytest.raises(ValidationError):
        ReturnCreate(order_id=1, reason="Prenda dañada", items=[{"order_item_id": 3, "quantity": 0}])


def test_flutter_eligibility_route_is_registered_before_dynamic_detail_route():
    source = Path("app/api/routes/returns.py").read_text(encoding="utf-8")
    assert source.index('"/orders/{order_id}/eligibility"') < source.index('"/{request_id}"')
