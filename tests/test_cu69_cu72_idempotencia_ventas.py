"""CU69-CU72: contratos de reintento de venta offline, sin BD ni Cloudinary.

Ejecutar: python -m pytest tests/test_cu69_cu72_idempotencia_ventas.py -q
No sustituye pruebas PostgreSQL concurrentes de stock.
"""
from types import SimpleNamespace
from unittest.mock import MagicMock, patch
from uuid import UUID

import pytest

from app.schemas.sale import SaleCreate
from app.services.sale_service import SaleService

UUID_OP = UUID('aaaaaaaa-bbbb-4ccc-8ddd-eeeeeeeeeeee')


def payload(items=((21, 2),), customer_id=None, op=UUID_OP):
    return SaleCreate(
        branch_id=59,
        customer_id=customer_id,
        client_operation_id=op,
        items=[{'product_variant_id': sku, 'quantity': qty} for sku, qty in items],
    )


def previous_sale(*, tenant=3, cashier=15, branch=59, customer=None, items=((21, 2),)):
    return SimpleNamespace(
        id=1001, tenant_id=tenant, cashier_id=cashier,
        branch_id=branch, customer_id=customer,
        items=[SimpleNamespace(product_variant_id=sku, quantity=qty) for sku, qty in items],
    )


def setup_db(previous):
    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = previous
    return db


def actor():
    return SimpleNamespace(tenant_id=3, id=15)


def lookup(db, data=None):
    return SaleService._previous_client_sale(db, actor(), 59, data or payload())


def test_sin_uuid_no_consulta_operacion_previa():
    db = setup_db(previous_sale())
    assert lookup(db, payload(op=None)) is None
    db.query.assert_not_called()


def test_uuid_nuevo_no_tiene_venta_previa():
    db = setup_db(None)
    assert lookup(db) is None


@pytest.mark.parametrize('changes', [
    {'tenant': 7}, {'cashier': 16}, {'branch': 60}, {'customer': 24},
])
def test_uuid_de_otra_identidad_o_contexto_es_rechazado(changes):
    db = setup_db(previous_sale(**changes))
    with pytest.raises(PermissionError):
        lookup(db)


@pytest.mark.parametrize('cart', [
    ((21, 1),), ((21, 3),), ((22, 2),), ((21, 2), (23, 1)),
])
def test_mismo_uuid_con_carrito_distinto_es_rechazado(cart):
    db = setup_db(previous_sale(items=cart))
    with pytest.raises(ValueError, match='carrito'):
        lookup(db)


def test_mismo_uuid_y_carrito_retorna_venta_existente():
    db = setup_db(previous_sale())
    expected = {'id': 1001, 'status': 'PENDING'}
    with patch.object(SaleService, '_get', return_value=object()) as get_sale, \
         patch.object(SaleService, '_serialize', return_value=expected) as serialize:
        assert lookup(db) == expected
        get_sale.assert_called_once_with(db, 1001)
        serialize.assert_called_once()


def test_reordenar_items_no_rompe_reintento():
    db = setup_db(previous_sale(items=((21, 2), (23, 1))))
    with patch.object(SaleService, '_get', return_value=object()), \
         patch.object(SaleService, '_serialize', return_value={'id': 1001}):
        assert lookup(db, payload(items=((23, 1), (21, 2)))) == {'id': 1001}


def test_cliente_correcto_es_aceptado():
    db = setup_db(previous_sale(customer=24))
    with patch.object(SaleService, '_get', return_value=object()), \
         patch.object(SaleService, '_serialize', return_value={'id': 1001}):
        assert lookup(db, payload(customer_id=24)) == {'id': 1001}
