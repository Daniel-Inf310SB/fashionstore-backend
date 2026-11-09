-- BLOQUE 5: ejecutar después del seed, no modifica datos.
SELECT t.name, r.name AS rol, COUNT(*) AS clientes
FROM users u JOIN tenants t ON t.id=u.tenant_id JOIN roles r ON r.id=u.role_id
WHERE r.name='CLIENTE' GROUP BY t.name,r.name ORDER BY t.name;

SELECT t.slug,
 (SELECT COUNT(*) FROM sales s WHERE s.tenant_id=t.id AND s.sale_code LIKE 'DEMO-B5-%') AS ventas,
 (SELECT COUNT(*) FROM orders o WHERE o.tenant_id=t.id AND o.order_code LIKE 'DEMO-B5-%') AS pedidos,
 (SELECT COUNT(*) FROM reservations r WHERE r.tenant_id=t.id AND r.reservation_code LIKE 'DEMO-B5-%') AS reservas,
 (SELECT COUNT(*) FROM shopping_carts c JOIN users u ON u.id=c.customer_id WHERE u.tenant_id=t.id) AS carritos
FROM tenants t ORDER BY t.id;

SELECT t.name, s.status, COUNT(*) FROM sales s JOIN tenants t ON t.id=s.tenant_id
WHERE s.sale_code LIKE 'DEMO-B5-%' GROUP BY t.name,s.status ORDER BY 1,2;
SELECT t.name, o.status, COUNT(*) FROM orders o JOIN tenants t ON t.id=o.tenant_id
WHERE o.order_code LIKE 'DEMO-B5-%' GROUP BY t.name,o.status ORDER BY 1,2;

-- Pagos y comprobantes por fuente comercial
SELECT 'SALE' AS origen, COUNT(DISTINCT s.id) AS operaciones,
       COUNT(DISTINCT p.id) AS pagos, COUNT(DISTINCT r.id) AS comprobantes
FROM sales s LEFT JOIN payments p ON p.sale_id=s.id
 LEFT JOIN receipts r ON r.sale_id=s.id WHERE s.sale_code LIKE 'DEMO-B5-%'
UNION ALL
SELECT 'ORDER',COUNT(DISTINCT o.id),COUNT(DISTINCT p.id),COUNT(DISTINCT r.id)
FROM orders o LEFT JOIN payments p ON p.order_id=o.id
 LEFT JOIN receipts r ON r.order_id=o.id WHERE o.order_code LIKE 'DEMO-B5-%';

-- Deben ser cero
SELECT COUNT(*) AS operaciones_cruzadas FROM (
 SELECT s.id FROM sales s JOIN branches b ON b.id=s.branch_id
 WHERE s.tenant_id IS DISTINCT FROM b.tenant_id
 UNION ALL
 SELECT o.id FROM orders o JOIN branches b ON b.id=o.branch_id
 WHERE o.tenant_id IS DISTINCT FROM b.tenant_id
 UNION ALL
 SELECT r.id FROM reservations r JOIN branches b ON b.id=r.branch_id
 WHERE r.tenant_id IS DISTINCT FROM b.tenant_id
) x;

SELECT COUNT(*) AS stock_negativo FROM inventories WHERE stock_quantity < 0 OR reserved_quantity > stock_quantity;

-- Conciliación del movimiento final contra el stock actual: pueden existir operaciones posteriores;
-- el último movimiento por inventario debe concordar con stock_quantity.
WITH ultima AS (
 SELECT DISTINCT ON (inventory_id) inventory_id,stock_after,reserved_after
 FROM inventory_movements ORDER BY inventory_id,created_at DESC,id DESC
)
SELECT COUNT(*) AS inventarios_desconciliados
FROM ultima m JOIN inventories i ON i.id=m.inventory_id
WHERE m.stock_after<>i.stock_quantity OR m.reserved_after<>i.reserved_quantity;
