-- BLOQUE 6 | Solo lectura. Ejecutar en fashionstore_db.
SELECT current_database() AS base_actual;
SELECT id,name,slug,is_active FROM tenants ORDER BY id;

-- Conteos por tenant (evita multiplicación de filas).
SELECT t.slug,
 (SELECT count(*) FROM branches b WHERE b.tenant_id=t.id) sucursales,
 (SELECT count(*) FROM users u WHERE u.tenant_id=t.id) usuarios,
 (SELECT count(*) FROM products p WHERE p.tenant_id=t.id) productos,
 (SELECT count(*) FROM orders o WHERE o.tenant_id=t.id) pedidos,
 (SELECT count(*) FROM sales s WHERE s.tenant_id=t.id) ventas,
 (SELECT count(*) FROM reservations r WHERE r.tenant_id=t.id) reservas
FROM tenants t ORDER BY t.id;

-- Relaciones cruzadas (cada cifra debe ser cero).
SELECT 'producto_categoria' prueba, count(*) fallos
 FROM products p JOIN categories c ON c.id=p.category_id
 WHERE p.tenant_id IS DISTINCT FROM c.tenant_id
UNION ALL SELECT 'producto_proveedor',count(*)
 FROM supplier_products sp JOIN suppliers s ON s.id=sp.supplier_id JOIN products p ON p.id=sp.product_id
 WHERE s.tenant_id IS DISTINCT FROM p.tenant_id
UNION ALL SELECT 'inventario_sucursal_producto',count(*)
 FROM inventories i JOIN branches b ON b.id=i.branch_id
 JOIN product_variants v ON v.id=i.product_variant_id JOIN products p ON p.id=v.product_id
 WHERE b.tenant_id IS DISTINCT FROM p.tenant_id
UNION ALL SELECT 'empleado_sucursal',count(*)
 FROM employee_branches eb JOIN users u ON u.id=eb.user_id JOIN branches b ON b.id=eb.branch_id
 WHERE u.tenant_id IS DISTINCT FROM b.tenant_id
UNION ALL SELECT 'venta_sucursal',count(*)
 FROM sales s JOIN branches b ON b.id=s.branch_id
 WHERE s.tenant_id IS DISTINCT FROM b.tenant_id
UNION ALL SELECT 'venta_cajero',count(*)
 FROM sales s JOIN users u ON u.id=s.cashier_id
 WHERE s.tenant_id IS DISTINCT FROM u.tenant_id
UNION ALL SELECT 'venta_cliente',count(*)
 FROM sales s JOIN users u ON u.id=s.customer_id
 WHERE s.tenant_id IS DISTINCT FROM u.tenant_id
UNION ALL SELECT 'pedido_sucursal',count(*)
 FROM orders o JOIN branches b ON b.id=o.branch_id
 WHERE o.tenant_id IS DISTINCT FROM b.tenant_id
UNION ALL SELECT 'pedido_cliente',count(*)
 FROM orders o JOIN users u ON u.id=o.customer_id
 WHERE o.tenant_id IS DISTINCT FROM u.tenant_id
UNION ALL SELECT 'reserva_sucursal',count(*)
 FROM reservations r JOIN branches b ON b.id=r.branch_id
 WHERE r.tenant_id IS DISTINCT FROM b.tenant_id
UNION ALL SELECT 'reserva_cliente',count(*)
 FROM reservations r JOIN users u ON u.id=r.customer_id
 WHERE r.tenant_id IS DISTINCT FROM u.tenant_id
UNION ALL SELECT 'item_venta_producto',count(*)
 FROM sale_items si JOIN sales s ON s.id=si.sale_id
 JOIN product_variants v ON v.id=si.product_variant_id JOIN products p ON p.id=v.product_id
 WHERE s.tenant_id IS DISTINCT FROM p.tenant_id
UNION ALL SELECT 'item_pedido_producto',count(*)
 FROM order_items oi JOIN orders o ON o.id=oi.order_id
 JOIN product_variants v ON v.id=oi.product_variant_id JOIN products p ON p.id=v.product_id
 WHERE o.tenant_id IS DISTINCT FROM p.tenant_id
UNION ALL SELECT 'pago_venta_usuario',count(*)
 FROM payments pay JOIN sales s ON s.id=pay.sale_id JOIN users u ON u.id=pay.user_id
 WHERE s.tenant_id IS DISTINCT FROM u.tenant_id
UNION ALL SELECT 'pago_pedido_usuario',count(*)
 FROM payments pay JOIN orders o ON o.id=pay.order_id JOIN users u ON u.id=pay.user_id
 WHERE o.tenant_id IS DISTINCT FROM u.tenant_id
UNION ALL SELECT 'movimiento_proveedor',count(*)
 FROM inventory_movements im JOIN suppliers s ON s.id=im.supplier_id
 JOIN inventories i ON i.id=im.inventory_id JOIN branches b ON b.id=i.branch_id
 WHERE s.tenant_id IS DISTINCT FROM b.tenant_id
ORDER BY prueba;

-- Totales pagos aprobados vs transacciones, por registro (diferencias requieren investigación;
-- una operación podría ser parcialmente pagada según las reglas de negocio).
SELECT 'venta' tipo, s.tenant_id, s.id, s.sale_code codigo, s.status,
 s.total_amount total, COALESCE(SUM(pay.amount) FILTER (WHERE pay.status='APPROVED'),0) pagado
FROM sales s LEFT JOIN payments pay ON pay.sale_id=s.id
GROUP BY s.id
HAVING s.total_amount IS DISTINCT FROM COALESCE(SUM(pay.amount) FILTER (WHERE pay.status='APPROVED'),0)
UNION ALL
SELECT 'pedido',o.tenant_id,o.id,o.order_code,o.status,o.total_amount,
 COALESCE(SUM(pay.amount) FILTER (WHERE pay.status='APPROVED'),0)
FROM orders o LEFT JOIN payments pay ON pay.order_id=o.id
GROUP BY o.id
HAVING o.total_amount IS DISTINCT FROM COALESCE(SUM(pay.amount) FILTER (WHERE pay.status='APPROVED'),0)
ORDER BY tipo,tenant_id,id;

-- Comprobantes por empresa, enlazados a pedidos o ventas.
SELECT t.slug, count(r.id) comprobantes
FROM tenants t LEFT JOIN (
 SELECT r.id, s.tenant_id FROM receipts r JOIN sales s ON s.id=r.sale_id
 UNION ALL SELECT r.id, o.tenant_id FROM receipts r JOIN orders o ON o.id=r.order_id
) r ON r.tenant_id=t.id GROUP BY t.id,t.slug ORDER BY t.id;

-- Estado inventarios, existencias y movimientos (no altera stock).
SELECT t.slug, COUNT(*) inventarios, SUM(i.stock_quantity) stock,
 SUM(i.reserved_quantity) reservado,
 COUNT(*) FILTER (WHERE i.stock_quantity < 0 OR i.reserved_quantity > i.stock_quantity) invalidos
FROM inventories i JOIN branches b ON b.id=i.branch_id JOIN tenants t ON t.id=b.tenant_id
GROUP BY t.id,t.slug ORDER BY t.id;
SELECT t.slug, im.movement_type, COUNT(*) movimientos, SUM(im.quantity) unidades
FROM inventory_movements im JOIN inventories i ON i.id=im.inventory_id
JOIN branches b ON b.id=i.branch_id JOIN tenants t ON t.id=b.tenant_id
GROUP BY t.id,t.slug,im.movement_type ORDER BY t.id,im.movement_type;
