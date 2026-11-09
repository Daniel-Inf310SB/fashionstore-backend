from decimal import Decimal
from types import SimpleNamespace
from app.services.sale_exchange_quote_service import money, paid_unit_amount


def test_cu77_discounted_unit_209():
    sale = SimpleNamespace(subtotal=Decimal('897.00'), total_amount=Decimal('807.30'))
    line = SimpleNamespace(unit_price=Decimal('299.00'))
    assert paid_unit_amount(sale, line) == Decimal('269.10')


def test_cu77_money_rounding():
    assert money('2.345') == Decimal('2.35')
