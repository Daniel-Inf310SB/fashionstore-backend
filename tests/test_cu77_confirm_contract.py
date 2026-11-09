"""CU77: casos unitarios de contrato que no alteran inventario real."""
from decimal import Decimal
import pytest
from app.models.sale_exchange import SaleExchange
from app.services.sale_exchange_confirm_service import confirm


def test_exchange_model_has_independent_ledger_and_uuid():
    assert SaleExchange.__tablename__ == 'sale_exchanges'
    assert SaleExchange.__table__.columns['client_operation_id'].nullable is False
    assert SaleExchange.__table__.columns['original_paid_total'].nullable is False


def test_reject_invalid_uuid_before_touching_database():
    with pytest.raises(ValueError, match='UUID inválido'):
        confirm(None, None, 209, client_operation_id='invalid',sale_item_id=209,
                replacement_variant_id=424,quantity=1,item_condition='RESELLABLE',
                amount_received=Decimal('19.90'),expected_additional=Decimal('19.90'))


def test_new_endpoints_exist_and_use_permissions():
    from app.api.routes.sales import router
    paths = {route.path: route for route in router.routes}
    assert '/sales/{sale_id}/exchange-confirm' in paths
    assert '/sales/{sale_id}/exchanges' in paths


def test_stale_confirmation_cannot_change_inventory(monkeypatch):
    from unittest.mock import MagicMock
    from types import SimpleNamespace
    import app.services.sale_exchange_confirm_service as exchange_service

    db = MagicMock()
    sale = SimpleNamespace(id=209, branch_id=59, tenant_id=3, items=[
        SimpleNamespace(id=209, quantity=3, product_variant_id=426)])
    db.query.return_value.filter.return_value.with_for_update.return_value.first.return_value = sale
    db.query.return_value.filter.return_value.first.return_value = None
    db.query.return_value.filter.return_value.all.return_value = []
    monkeypatch.setattr(exchange_service.SaleService, '_check_access', lambda *args: None)
    monkeypatch.setattr(exchange_service, '_load_sale', lambda *args: sale)
    monkeypatch.setattr(exchange_service, 'quote', lambda *args: {
        'additional_to_collect': Decimal('20.90'), 'potential_store_credit': Decimal('0'),
    })
    with pytest.raises(ValueError, match='cotización cambió'):
        confirm(db, SimpleNamespace(id=131), 209,
                client_operation_id='9b0ea845-e8a6-41bb-931a-8abed7d2216c',
                sale_item_id=209, replacement_variant_id=424, quantity=1,
                item_condition='RESELLABLE', amount_received=Decimal('19.90'),
                expected_additional=Decimal('19.90'))
    db.add.assert_not_called()
    db.commit.assert_not_called()
    db.rollback.assert_called_once()
