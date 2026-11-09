"""Bloque 6: inspección read-only, sin seeds ni commits."""
import argparse
from pathlib import Path
from sqlalchemy import text
from app.database.session import SessionLocal
from app.database.seeds.seed_demo_config import DEMO_TENANTS

EXPECTED_DB = 'fashionstore_db'
CHECKS = {
    'tenants_esperados': "SELECT COUNT(*) FROM tenants WHERE slug IN ('fashionstore','urban-style-demo','technova-store') AND is_active",
    'productos_sin_empresa': 'SELECT COUNT(*) FROM products WHERE tenant_id IS NULL',
    'ventas_sin_empresa': 'SELECT COUNT(*) FROM sales WHERE tenant_id IS NULL',
    'pedidos_sin_empresa': 'SELECT COUNT(*) FROM orders WHERE tenant_id IS NULL',
    'inventarios_cruzados': '''SELECT COUNT(*) FROM inventories i
        JOIN branches b ON b.id=i.branch_id
        JOIN product_variants v ON v.id=i.product_variant_id
        JOIN products p ON p.id=v.product_id
        WHERE b.tenant_id IS DISTINCT FROM p.tenant_id''',
    'asignaciones_cruzadas': '''SELECT COUNT(*) FROM employee_branches eb
        JOIN branches b ON b.id=eb.branch_id JOIN users u ON u.id=eb.user_id
        WHERE b.tenant_id IS DISTINCT FROM u.tenant_id''',
     'clientes_sin_tenant': "SELECT COUNT(*) FROM users u JOIN roles r ON r.id=u.role_id WHERE r.name='CLIENTE' AND u.tenant_id IS NULL",
    'ventas_cliente_cruzado': "SELECT COUNT(*) FROM sales s JOIN users u ON u.id=s.customer_id WHERE u.tenant_id IS DISTINCT FROM s.tenant_id",
    'pedidos_cliente_cruzado': "SELECT COUNT(*) FROM orders o JOIN users u ON u.id=o.customer_id WHERE u.tenant_id IS DISTINCT FROM o.tenant_id",
    'ventas_sucursal_cruzada': "SELECT COUNT(*) FROM sales s JOIN branches b ON b.id=s.branch_id WHERE b.tenant_id IS DISTINCT FROM s.tenant_id",
    'pedidos_sucursal_cruzada': "SELECT COUNT(*) FROM orders o JOIN branches b ON b.id=o.branch_id WHERE b.tenant_id IS DISTINCT FROM o.tenant_id",
    'promociones_cruzadas': """SELECT COUNT(*) FROM product_promotions pp JOIN products p ON p.id=pp.product_id JOIN promotions pr ON pr.id=pp.promotion_id WHERE p.tenant_id IS DISTINCT FROM pr.tenant_id""",
    'colecciones_cruzadas': """SELECT COUNT(*) FROM product_collections pc JOIN products p ON p.id=pc.product_id JOIN collections c ON c.id=pc.collection_id WHERE p.tenant_id IS DISTINCT FROM c.tenant_id""",
    'notificaciones_marketing_cruzadas': """SELECT COUNT(*) FROM notifications n JOIN users u ON u.id=n.user_id JOIN promotions p ON p.id=n.entity_id WHERE n.dedupe_key LIKE 'DEMO-MARKETING-NOTICE-%' AND n.entity_type='PROMOTION' AND u.tenant_id IS DISTINCT FROM p.tenant_id""",
    'stock_invalido': '''SELECT COUNT(*) FROM inventories
        WHERE stock_quantity < 0 OR reserved_quantity < 0 OR reserved_quantity > stock_quantity''',
}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirm', action='store_true', help='Confirma ejecución solo lectura')
    args = parser.parse_args()
    if not args.confirm:
        parser.error('Usa --confirm para validar en modo solo lectura')
    with SessionLocal() as session:
        db = session.scalar(text('SELECT current_database()'))
        if db != EXPECTED_DB:
            raise RuntimeError(f'Base inesperada: {db}')
        print('Validando:', db)
        failures = []
        for key, query in CHECKS.items():
            value = session.scalar(text(query))
            success = (value == 3) if key == 'tenants_esperados' else (value == 0)
            print(f'{"OK" if success else "REVISAR"} | {key}: {value}')
            if not success:
                failures.append(key)
        session.rollback()  # Sin cambios, explícitamente read-only.
    if failures:
        raise SystemExit('Se encontraron alertas: ' + ', '.join(failures))
    print('Comprobaciones de integridad básicas aprobadas.')

if __name__ == '__main__':
    main()
