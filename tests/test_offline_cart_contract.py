"""Contract tests: backend response compatibility and stable offline errors."""
from uuid import uuid4
import pytest
from app.core.commercial_errors import commercial_error_headers
from app.schemas.cart import CartItemAddRequest
from app.services.cart_service import CartOperationConflict


def test_legacy_cart_payload_still_valid():
    assert CartItemAddRequest(branch_id=1, product_variant_id=3, quantity=2).client_operation_id is None


def test_offline_cart_payload_uuid_round_trips():
    value = uuid4()
    payload = CartItemAddRequest(branch_id=1, product_variant_id=3, quantity=2, client_operation_id=value)
    assert payload.client_operation_id == value


def test_invalid_uuid_rejected():
    with pytest.raises(Exception):
        CartItemAddRequest(branch_id=1, product_variant_id=3, quantity=2, client_operation_id="not-a-uuid")


@pytest.mark.parametrize("error,code", [
    (ValueError("Solo hay 2 unidades disponibles de esta variante."), "INSUFFICIENT_STOCK"),
    (LookupError("La variante está desactivada."), "VARIANT_UNAVAILABLE"),
    (ValueError("Ya tienes una reserva PENDING en esta sucursal."), "EXISTING_PENDING_RESERVATION"),
    (ValueError("El UUID ya se utilizó con datos diferentes."), "OPERATION_ID_CONFLICT"),
    (PermissionError("No puedes usar esta empresa."), "FORBIDDEN"),
])
def test_error_codes_are_stable(error, code):
    assert commercial_error_headers(error)["X-FS-Error-Code"] == code


def test_available_quantity_extracted_only_when_given():
    assert commercial_error_headers(ValueError("Solo hay 2 unidades disponibles."))["X-FS-Available-Quantity"] == "2"
    assert "X-FS-Available-Quantity" not in commercial_error_headers(ValueError("No hay stock disponible."))


def test_conflict_type_is_explicit():
    assert isinstance(CartOperationConflict("UUID already used"), ValueError)
