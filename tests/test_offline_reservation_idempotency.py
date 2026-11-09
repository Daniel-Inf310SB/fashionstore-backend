"""Contratos del UUID de reservas sin necesidad de PostgreSQL.

Ejecutar: python -m pytest tests/test_offline_reservation_idempotency.py -q
No sustituye una prueba de concurrencia real contra PostgreSQL.
"""
from types import SimpleNamespace

from app.core.reservation_idempotency import reservation_operation_fingerprint


def fingerprint(items, *, branch=5, customer=8, notes=None):
    lines = [SimpleNamespace(product_variant_id=variant, quantity=quantity)
             for variant, quantity in items]
    return reservation_operation_fingerprint(
        branch_id=branch, customer_id=customer, items=lines, notes=notes
    )


def test_reordenar_prendas_no_modifica_uuid_semantico():
    assert fingerprint([(12, 2), (15, 1)]) == fingerprint([(15, 1), (12, 2)])


def test_variantes_repetidas_se_agrupan_para_mismo_reintento():
    assert fingerprint([(12, 1), (12, 2)]) == fingerprint([(12, 3)])


def test_distinta_cantidad_no_es_el_mismo_envio():
    assert fingerprint([(12, 2)]) != fingerprint([(12, 3)])


def test_distinto_tenant_scope_por_sucursal_o_cliente_no_es_el_mismo_envio():
    original = fingerprint([(12, 2)])
    assert original != fingerprint([(12, 2)], branch=6)
    assert original != fingerprint([(12, 2)], customer=9)


def test_cambiar_notas_modifica_el_contenido_de_la_operacion():
    assert fingerprint([(12, 2)], notes="entregar sábado") != fingerprint([(12, 2)], notes="entregar lunes")
