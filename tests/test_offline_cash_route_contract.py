"""Contract checks for the offline cash POS route, without database access.

The full transaction still needs PostgreSQL integration tests.
"""
import ast
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


def get_tree(filename: str) -> ast.Module:
    return ast.parse((ROOT / filename).read_text(encoding="utf-8"))


def function_by_name(tree: ast.AST, name: str):
    return next(node for node in ast.walk(tree)
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name)


class OfflineCashContract(unittest.TestCase):
    def test_request_requires_operation_uuid_and_amount(self):
        tree = get_tree('app/api/routes/sales.py')
        request = next(node for node in tree.body if isinstance(node, ast.ClassDef) and node.name == 'OfflineCashSaleRequest')
        attrs = {node.target.id for node in request.body if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name)}
        self.assertTrue({'client_operation_id', 'branch_id', 'amount_received'}.issubset(attrs))

    def test_create_and_payment_can_join_same_transaction(self):
        sale = function_by_name(get_tree('app/services/sale_service.py'), 'create_sale')
        cash = function_by_name(get_tree('app/services/cash_payment_service.py'), 'process')
        for fn in [sale, cash]:
            self.assertIn('commit', [arg.arg for arg in fn.args.kwonlyargs])
        endpoint = function_by_name(get_tree('app/api/routes/sales.py'), 'create_offline_cash_sale')
        source = ast.unparse(endpoint)
        self.assertIn('commit=False', source)
        self.assertIn('db.commit()', source)
        self.assertIn('db.rollback()', source)
        self.assertIn('client_operation_id', source)
        self.assertIn('previous = existing_paid()', source)

    def test_path_does_not_override_existing_sale_route(self):
        tree = get_tree('app/api/routes/sales.py')
        endpoint = function_by_name(tree, 'create_offline_cash_sale')
        decorator = '\n'.join(ast.unparse(d) for d in endpoint.decorator_list)
        self.assertIn('/offline-cash', decorator)


if __name__ == '__main__':
    unittest.main()
