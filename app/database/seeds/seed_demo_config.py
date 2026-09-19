from __future__ import annotations

from datetime import date

# Dataset de demostración 2026: compacto, realista e idempotente.
SEED_YEAR = 2026
SEED_UNTIL = date(2026, 9, 18)

# Catálogo
PRODUCT_COUNT = 200
VARIANTS_PER_PRODUCT = 3

# Clientes
CUSTOMER_COUNT = 10
SEED_PASSWORD = "Cliente123*"

# Comercio histórico
# Se distribuyen entre todas las sucursales con personal activo.
SALES_TOTAL = 180
ORDERS_TOTAL = 90
RESERVATIONS_TOTAL = 54

# Carritos (máximo 1 por cliente en este seed)
ACTIVE_CARTS = 6
ABANDONED_CARTS = 3
