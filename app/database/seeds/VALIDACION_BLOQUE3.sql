SELECT t.slug, COUNT(DISTINCT p.id) AS productos, COUNT(DISTINCT v.id) AS variantes
FROM tenants t LEFT JOIN products p ON p.tenant_id=t.id
LEFT JOIN product_variants v ON v.product_id=p.id
GROUP BY t.id,t.slug ORDER BY t.id;

SELECT t.slug,COUNT(DISTINCT s.id) AS proveedores,COUNT(DISTINCT sp.id) AS proveedor_productos
FROM tenants t LEFT JOIN suppliers s ON s.tenant_id=t.id
LEFT JOIN supplier_products sp ON sp.supplier_id=s.id
GROUP BY t.id,t.slug ORDER BY t.id;

SELECT COUNT(*) AS relaciones_cruzadas FROM supplier_products sp
JOIN suppliers s ON s.id=sp.supplier_id
JOIN products p ON p.id=sp.product_id
WHERE s.tenant_id IS DISTINCT FROM p.tenant_id;
SELECT COUNT(*) AS productos_categoria_cruzada FROM products p
JOIN categories c ON c.id=p.category_id
WHERE p.tenant_id IS DISTINCT FROM c.tenant_id;
