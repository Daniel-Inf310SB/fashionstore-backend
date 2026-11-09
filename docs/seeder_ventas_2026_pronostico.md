# FashionStore: ventas académicas 2026 para pronóstico ML

Se agrega `app/scripts/seed_sales_2026_forecast.py`. Se usa el endpoint existente `/analytics/ml/tenant/forecast` y su mínimo de **90 días desde la primera venta** y **20 días con ventas pagadas** por tenant.

## Qué genera

- Desde **2026-01-01** hasta la fecha `--until` (por defecto el día actual UTC, nunca una fecha futura).
- Una venta **PAID** cada día y una segunda los sábados y domingos, para cada tenant seleccionado.
- `Sale`, `SaleItem`, `Payment` aprobado, decremento de inventario y `InventoryMovement` de venta, con sucursal/cajero/variante del mismo tenant.
- Códigos persistentes `AF26-<slug>-<AAAAMMDD>-<nn>`, por lo que **repetir la misma ejecución no duplica ventas**.
- Dry-run predeterminado, validación de stock para todo el lote y una única transacción para los tres tenants. Si falla una empresa, ninguna se confirma.

## Requisitos previos

1. Ejecutar migraciones Alembic y tener creados los tres tenants, catálogos, variantes, inventarios y cajeros asignados.
2. **Respaldar PostgreSQL**. Estas ventas son ficticias pero afectan ingresos, stock y otros reportes. **Nunca ejecutar en producción**.
3. Preferible: restaurar `fashionstore_db` en una copia llamada `fashionstore_demo` o `fashionstore_test` y apuntar `DATABASE_URL` a esa copia.

## Ejecutar desde la raíz `fashionstore_api` en PowerShell

Para la base local habitual `fashionstore_db` (solo desarrollo):

```powershell
python -m app.scripts.seed_sales_2026_forecast --year 2026 --until 2026-11-07 --allow-current-db
```

Revisa los tres resúmenes, sobre todo `to_create`, y confirma luego:

```powershell
python -m app.scripts.seed_sales_2026_forecast --year 2026 --until 2026-11-07 --allow-current-db --apply --confirm DEMO_2026
```

En una copia `fashionstore_demo` / `fashionstore_test` basta omitir `--allow-current-db`. Para un solo tenant usa `--tenant fashionstore`, `--tenant urban-style-demo` o `--tenant technova-store`.

## Comprobación SQL

```sql
SELECT t.name, MIN(s.created_at)::date AS primera_venta,
       MAX(s.created_at)::date AS ultima_venta,
       COUNT(DISTINCT s.created_at::date) AS dias_con_ventas,
       COUNT(*) AS ventas_2026,
       SUM(s.total_amount) AS importe_bob
FROM sales s JOIN tenants t ON t.id=s.tenant_id
WHERE s.sale_code LIKE 'AF26-%' AND s.status='PAID'
GROUP BY t.id, t.name ORDER BY t.id;
```

Reinicia la sesión web o pulsa «Actualizar» en Analítica inteligente. Solo los tenants con plan que incluya `ai_reports`, suscripción vigente y permiso `reports.view` pueden acceder a esa función: **TechNova Básico no tiene habilitada IA en el catálogo original**, aunque tenga ventas académicas.

## Limitaciones

- Es un **historial sintético retroactivo**: no demuestra precisión comercial real ni sustituye pruebas de venta normal.
- Consume stock disponible de la base demo. Si el inventario es insuficiente, la operación se cancela sin insertar ventas parciales: no recomendamos inventar entradas de proveedor o permitir existencias negativas.
- Al usar ventas de contado para el experimento, se afectan también los dashboards de ventas y rotación; trabaja sobre una copia recuperable.
- No genera ventas de fechas posteriores al día actual, aunque se pida el año completo. Para el resto de 2026 se podrá volver a ejecutar más adelante; los días existentes no se duplicarán.
