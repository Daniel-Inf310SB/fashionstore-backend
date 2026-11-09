# FashionStore — motor unificado de postventa

## Objetivo

`/post-sale` centraliza las solicitudes de devolución y cambio para pedidos online (`ONLINE`) y ventas presenciales (`POS`). Conserva las tablas y endpoints históricos para compatibilidad, pero los nuevos flujos deben usar el motor unificado.

## Migración

La revisión nueva es `e1d20261107_unified_post_sale`, hija de `d0d20261106`.

Antes de aplicar:
1. Haz backup de PostgreSQL.
2. Confirma `alembic current` y `alembic heads`.
3. Ejecuta `alembic upgrade head`.
4. Reinicia FastAPI.

No ejecutes `stamp` ni borres revisiones si hay divergencia. Si `alembic heads` devuelve más de una cabeza, detente y revisa el grafo.

## Canales y elegibilidad

- `ONLINE`: debe ser un pedido del cliente autenticado, con pago aprobado y entrega final registrada. Se aplica el plazo de 7 días desde `delivered_at` para envío o `completed_at` para retiro en sucursal.
- `POS`: debe ser una venta pagada, asociada al cliente autenticado para autoservicio, con pago aprobado y dentro de 7 días desde la venta.
- Ventas POS sin cuenta de cliente: el encargado o administrador puede registrar el caso mediante `/cases/staff-assisted`.
- Las cantidades ya solicitadas, recibidas, devueltas o cambiadas se descuentan de la elegibilidad, incluyendo los flujos legacy existentes.

## Flujo

1. Cliente consulta elegibilidad.
2. Cliente crea caso `REFUND` o `EXCHANGE`.
3. Encargado de la sucursal revisa y aprueba/rechaza.
4. Encargado recibe los artículos físicamente.
5. Encargado inspecciona cada artículo: `RESELLABLE`, `DAMAGED` o `QUARANTINE`.
6. Para `REFUND`, el backend calcula el importe original a reintegrar.
7. Para `EXCHANGE`, el personal cotiza las nuevas variantes y el backend compara el valor realmente pagado con el precio actual de las prendas de reemplazo.
8. Diferencia positiva: el encargado registra el cobro en sucursal (`CASH`, `CARD`, `QR`, `TRANSFER`) con referencia para métodos no efectivos.
9. Diferencia negativa: el administrador autoriza el reintegro de la diferencia.
10. Diferencia cero: no se necesita liquidación.
11. Personal autorizado completa el caso. En una sola transacción se registran movimientos de inventario y se cierra el caso.

## Tipos cubiertos

- Devolución total o parcial de artículos de un pedido/venta.
- Cambio por el mismo valor.
- Cambio por mayor valor y cobro de diferencia.
- Cambio por menor valor y reintegro de diferencia.
- Reembolso completo o parcial.
- Artículos aptos para reventa, dañados o en cuarentena.
- Compras online y presenciales.
- Venta POS asociada o no a una cuenta de cliente.

El reintegro de una diferencia menor se hace como reembolso, no como saldo de monedero. FashionStore todavía no tiene un monedero de cliente integrado a checkout/caja; no se emite un saldo ficticio que luego no pueda consumirse.

## Endpoints

- `GET /post-sale/eligibility/{ONLINE|POS}/{source_id}`
- `POST /post-sale/cases`
- `POST /post-sale/cases/staff-assisted`
- `GET /post-sale/cases/mine`
- `GET /post-sale/cases`
- `GET /post-sale/cases/{case_id}`
- `POST /post-sale/cases/{case_id}/decision`
- `POST /post-sale/cases/{case_id}/receive`
- `POST /post-sale/cases/{case_id}/inspection`
- `POST /post-sale/cases/{case_id}/quote`
- `POST /post-sale/cases/{case_id}/settlement`
- `POST /post-sale/cases/{case_id}/settlement/reconcile-stripe`
- `POST /post-sale/cases/{case_id}/complete`
- `POST /post-sale/cases/{case_id}/cancel`

## Liquidaciones y seguridad financiera

- `COLLECT`: solo personal autorizado de la sucursal registra el cobro de una diferencia; el monto debe coincidir exactamente con la cotización del servidor.
- `DEMO_LOCAL`: solo funciona si `FASHIONSTORE_ENABLE_DEMO_REFUNDS=true` y todos los pagos originales están marcados explícitamente como `DEMO_LOCAL`. No mueve dinero real.
- `EXTERNAL_MANUAL`: el administrador registra una constancia externa. Es una declaración auditada; no ejecuta una transferencia bancaria.
- `STRIPE_TEST`: solo online, con `STRIPE_SECRET_KEY=sk_test_...`, un PaymentIntent original aprobado y metadatos coincidentes. Si Stripe devuelve un resultado incierto, el caso queda `PROCESSING` y debe conciliarse; no se repite a ciegas.
- El encargado puede aprobar, recibir, inspeccionar y registrar cobros de diferencias; solo el administrador puede autorizar reembolsos.
- El importe acumulado de reintegros se valida contra los pagos aprobados y los reembolsos legacy/unificados para evitar superar lo cobrado.

## Inventario

- Los artículos devueltos solo vuelven a stock vendible si la inspección es `RESELLABLE`.
- `DAMAGED` y `QUARANTINE` quedan fuera del stock disponible; la inspección queda registrada.
- Las prendas de reemplazo se descuentan al completar el caso.
- Todos los movimientos se registran en `inventory_movements` con `reference_type=POST_SALE_CASE`.
- El movimiento de devolución/reemplazo y el cierre del caso ocurren dentro de la misma transacción.

## Compatibilidad legacy

Los endpoints históricos `/returns`, `/sale-returns` y los reembolsos existentes siguen disponibles para no romper pantallas actuales. Sus controles de elegibilidad y topes de reembolso ahora consideran los casos unificados para evitar reutilizar unidades o devolver más dinero del cobrado.

La confirmación directa legacy `/sales/{sale_id}/exchange-confirm` queda deshabilitada: los cambios nuevos deben pasar por `/post-sale/cases` para garantizar aprobación, recepción, inspección y liquidación. Las cotizaciones antiguas pueden seguir utilizándose como consulta temporal, pero la cotización definitiva debe hacerse con `/post-sale/cases/{case_id}/quote`.

## Ejemplos de payload

Crear solicitud desde Flutter:

```json
{
  "source_channel": "POS",
  "source_id": 151,
  "resolution_type": "EXCHANGE",
  "reason": "La talla no corresponde",
  "items": [
    {"source_item_id": 802, "quantity": 1}
  ],
  "idempotency_key": "d8d8b5a0-ec90-4f2b-8a25-1d09b87cbf22"
}
```

Cotizar reemplazo:

```json
{
  "items": [
    {"product_variant_id": 945, "quantity": 1}
  ]
}
```

Inspección:

```json
{
  "items": [
    {"case_item_id": 1, "condition": "RESELLABLE", "note": "Prenda sin uso y con etiquetas"}
  ]
}
```

Registrar diferencia cobrada:

```json
{
  "amount": "30.00",
  "method": "QR",
  "reference": "QR-CAJA-000091"
}
```

Autorizar reintegro externo:

```json
{
  "amount": "20.00",
  "mode": "EXTERNAL_MANUAL",
  "reference": "TRANSFER-2026-000123"
}
```

## Verificación recomendada

1. Probar una devolución parcial online.
2. Probar un cambio online por igual valor.
3. Probar cambio POS por mayor valor y cobro de diferencia.
4. Probar cambio POS por menor valor con reintegro administrativo.
5. Probar un artículo dañado: no debe aumentar stock.
6. Probar dos solicitudes concurrentes para la misma unidad: solo una debe reservarla.
7. Probar que un encargado de una sucursal no pueda consultar ni gestionar otra.
8. Probar que un reembolso Stripe incierto permanezca en conciliación y no se emita dos veces.

La compilación de sintaxis Python y las pruebas unitarias de cálculo se ejecutaron en el entorno de preparación. La migración y los flujos Stripe/PostgreSQL deben probarse en la base local antes de producción.
