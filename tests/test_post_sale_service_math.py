from decimal import Decimal
from types import SimpleNamespace

from app.services.post_sale_service import PostSaleService, money


def test_money_uses_two_decimal_places():
    assert money("12.345") == Decimal("12.35")
    assert money("12.344") == Decimal("12.34")


def test_partial_return_uses_actual_paid_value_after_order_discount():
    source = SimpleNamespace(subtotal=Decimal("300.00"), total_amount=Decimal("270.00"))
    line = SimpleNamespace(quantity=3, subtotal=Decimal("150.00"), unit_price=Decimal("50.00"))
    # Two of three units from a line that represents half the pre-discount basket.
    assert PostSaleService._line_paid_total(source, line, 2) == Decimal("90.00")


def test_partial_pos_return_uses_actual_paid_value_after_sale_discount():
    source = SimpleNamespace(subtotal=Decimal("200.00"), total_amount=Decimal("180.00"))
    line = SimpleNamespace(quantity=2, subtotal=Decimal("100.00"), unit_price=Decimal("50.00"))
    assert PostSaleService._line_paid_total(source, line, 1) == Decimal("45.00")
