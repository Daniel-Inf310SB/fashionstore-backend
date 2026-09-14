from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

import app.models

from app.core.config import settings
from app.core.cloudinary_config import configure_cloudinary

from app.api.routes.auth import (
    router as auth_router,
)

from app.api.routes.roles import (
    router as roles_router,
)

from app.api.routes.permissions import (
    router as permissions_router,
)

from app.api.routes.users import (
    router as users_router,
)

from app.api.routes.audit_logs import (
    router as audit_logs_router,
)

from app.api.routes.cities import (
    router as cities_router,
)

from app.api.routes.branches import (
    router as branches_router,
)

from app.api.routes.employee_branches import (
    router as employee_branches_router,
)

from app.api.routes.categories import (
    router as categories_router,
)

from app.api.routes.sizes import (
    router as sizes_router,
)

from app.api.routes.audiences import (
    router as audiences_router,
)

from app.api.routes.colors import (
    router as colors_router,
)

from app.api.routes.seasons import (
    router as seasons_router,
)

from app.api.routes.collections import (
    router as collections_router,
)

from app.api.routes.promotions import (
    router as promotions_router,
)

from app.api.routes.cloudinary_test import (
    router as cloudinary_test_router,
)

from app.api.routes.products import (
    router as products_router,
)

from app.api.routes.product_images import (
    router as product_images_router,
)

from app.api.routes.product_variants import (
    router as product_variants_router,
)

from app.api.routes.product_associations import (
    router as product_associations_router,
)
from app.api.routes.store_branches import (
    router as store_branches_router,
)

# =========================================================
# MÓDULO 4 - PROVEEDORES
# =========================================================

from app.api.routes.suppliers import (
    router as suppliers_router,
)

from app.api.routes.supplier_products import (
    router as supplier_products_router,
)

from app.api.routes.supplier_availability import (
    router as supplier_availability_router,
)


# =========================================================
# MÓDULO 5 - INVENTARIO
# =========================================================

from app.api.routes.inventory import (
    router as inventory_router,
)

from app.api.routes.branch_stock import (
    router as branch_stock_router,
)

from app.api.routes.inventory_movements import (
    router as inventory_movements_router,
)

from app.api.routes.global_inventory import (
    router as global_inventory_router,
)


# =========================================================
# MÓDULO 6 - CATÁLOGO DEL CLIENTE
# =========================================================

from app.api.routes.customer_catalog import (
    router as customer_catalog_router,
)

from app.api.routes.customer_product_detail import (
    router as customer_product_detail_router,
)


# =========================================================
# CLOUDINARY
# =========================================================

configure_cloudinary()


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
)


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:4200",
    ],

    allow_credentials=True,

    allow_methods=[
        "*",
    ],

    allow_headers=[
        "*",
    ],
)


# =========================================================
# ROUTERS GENERALES
# =========================================================

app.include_router(
    auth_router
)

app.include_router(
    roles_router
)

app.include_router(
    permissions_router
)

app.include_router(
    users_router
)

app.include_router(
    audit_logs_router
)

app.include_router(
    cities_router
)

app.include_router(
    branches_router
)

app.include_router(
    employee_branches_router
)

app.include_router(
    categories_router
)

app.include_router(
    sizes_router
)

app.include_router(
    audiences_router
)

app.include_router(
    colors_router
)

app.include_router(
    seasons_router
)

app.include_router(
    collections_router
)

app.include_router(
    promotions_router
)

app.include_router(
    cloudinary_test_router
)

app.include_router(
    products_router
)

app.include_router(
    product_images_router
)

app.include_router(
    product_variants_router
)

app.include_router(
    product_associations_router
)


# =========================================================
# MÓDULO 4 - PROVEEDORES
# =========================================================

# CU17 - Gestionar proveedores
app.include_router(
    suppliers_router
)

# CU18 - Gestionar productos del proveedor
app.include_router(
    supplier_products_router
)

# CU19 - Gestionar disponibilidad del proveedor
app.include_router(
    supplier_availability_router
)


# =========================================================
# MÓDULO 5 - INVENTARIO
# =========================================================

# CU20 - Gestionar inventario
app.include_router(
    inventory_router
)

# CU21 - Existencias por sucursal
app.include_router(
    branch_stock_router
)

# CU22 - Gestionar movimientos de inventario
app.include_router(
    inventory_movements_router
)

# CU23 - Consultar inventario global
app.include_router(
    global_inventory_router
)


# =========================================================
# MÓDULO 6 - CATÁLOGO DEL CLIENTE
# =========================================================
# Seleccionar sucursal para la tienda
app.include_router(
    store_branches_router
)
# CU24 - Consultar catálogo
# CU25 - Buscar y filtrar prendas
app.include_router(
    customer_catalog_router
)

# CU26 - Consultar detalle de prenda
app.include_router(
    customer_product_detail_router
)


# =========================================================
# ROOT
# =========================================================

@app.get("/")
def root():
    return {
        "message":
            "FashionStore API funcionando"
    }


# =========================================================
# HEALTH
# =========================================================

@app.get("/health")
def health():
    return {
        "status":
            "ok"
    }