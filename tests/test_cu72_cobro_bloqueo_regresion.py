"""CU72: regresion estructural del flujo de cobro.

No simula dos transacciones PostgreSQL: verifica que el flujo conserve
los controles necesarios para serializar los cobros por inventario.
"""
import ast
import inspect
import textwrap

from app.services.cash_payment_service import CashPaymentService


def _method():
    return ast.parse(textwrap.dedent(inspect.getsource(CashPaymentService.process))).body[0]


def _calls(method, name):
    return [node for node in ast.walk(method) if isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute) and node.func.attr == name]


def _line(method, text):
    src = textwrap.dedent(inspect.getsource(CashPaymentService.process))
    for i, line in enumerate(src.splitlines(), 1):
        if text in line:
            return i
    raise AssertionError(f'No se encontro {text!r} en CashPaymentService.process')


def test_cu72_bloquea_venta_y_stock_antes_de_cobrar():
    method = _method()
    assert len(_calls(method, 'with_for_update')) >= 2, (
        'Se espera bloqueo de la venta y del inventario durante el cobro'
    )


def test_cu72_revalida_stock_despues_de_bloquear():
    method = _method()
    line_lock = max(n.lineno for n in _calls(method, 'with_for_update'))
    assert line_lock < _line(method, 'inventory.available_quantity')
    assert _line(method, 'inventory.available_quantity') < _line(method, 'inventory.stock_quantity = (')


def test_cu72_no_confirma_antes_de_descontar():
    method = _method()
    commits = _calls(method, 'commit')
    assert len(commits) == 1
    assert _line(method, 'inventory.stock_quantity = (') < commits[0].lineno


def test_cu72_responde_error_al_no_haber_stock():
    src = textwrap.dedent(inspect.getsource(CashPaymentService.process))
    assert 'inventory.available_quantity' in src
    assert 'Stock insuficiente para completar la venta' in src
