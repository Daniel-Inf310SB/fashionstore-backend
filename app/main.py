from fastapi import (
    FastAPI,
)

from fastapi.middleware.cors import (
    CORSMiddleware,
)

from apscheduler.schedulers.background import (
    BackgroundScheduler,
)

import app.models

from app.core.config import (
    settings,
)

from app.core.cloudinary_config import (
    configure_cloudinary,
)

from app.jobs.expiration_jobs import (
    run_expiration_jobs,
)

from app.jobs.notification_jobs import (
    run_marketing_notification_jobs,
    run_push_delivery_jobs,
)

from app.services.firebase_service import (
    FirebaseService,
)


# =========================================================
# MÓDULO 1 - AUTENTICACIÓN, USUARIOS Y PERMISOS
# =========================================================

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

from app.api.routes.notifications import (
    router as notifications_router,
)

from app.api.routes.devices import (
    router as devices_router,
)


# =========================================================
# MÓDULO 2 - SUCURSALES
# =========================================================

from app.api.routes.cities import (
    router as cities_router,
)

from app.api.routes.branches import (
    router as branches_router,
)

from app.api.routes.employee_branches import (
    router as employee_branches_router,
)


# =========================================================
# MÓDULO 3 - CATÁLOGO ADMINISTRATIVO
# =========================================================

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

from app.api.routes.cloudinary_test import (
    router as cloudinary_test_router,
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

from app.api.routes.store_branches import (
    router as store_branches_router,
)

from app.api.routes.customer_catalog import (
    router as customer_catalog_router,
)

from app.api.routes.customer_merchandising import (
    router as customer_merchandising_router,
)

from app.api.routes.customer_product_detail import (
    router as customer_product_detail_router,
)


# =========================================================
# MÓDULO 7 - RESERVAS
# =========================================================

from app.api.routes.reservations import (
    router as reservations_router,
)

# =========================================================
# MÓDULO 8 - CARRITO
# =========================================================

from app.api.routes.carts import (
    router as carts_router,
)

# =========================================================
# MÓDULO 9 - COMPRAS DIGITALES
# =========================================================

from app.api.routes.orders import (
    router as orders_router,
)


# =========================================================
# MÓDULO 10 - VENTAS PRESENCIALES
# =========================================================

from app.api.routes.sales import (
    router as sales_router,
)

from app.api.routes.cash_payments import (
    router as cash_payments_router,
)

from app.api.routes.receipts import (
    router as receipts_router,
)


# =========================================================
# MÓDULO 11 - PAGOS ELECTRÓNICOS
# =========================================================

from app.api.routes.payments import (
    router as payments_router,
)


# =========================================================
# MÓDULO 12 - REPORTES
# =========================================================

from app.api.routes.reports import (
    router as reports_router,
)


# =========================================================
# DASHBOARD ADMINISTRATIVO
# =========================================================

from app.api.routes.dashboard import (
    router as dashboard_router,
)


# =========================================================
# MÓDULO 13 - INTELIGENCIA ARTIFICIAL
# =========================================================

from app.api.routes.ai import (
    router as ai_router,
)

from app.api.routes.customer_assistant import (
    router as customer_assistant_router,
)


# =========================================================
# CLOUDINARY
# =========================================================

configure_cloudinary()


# =========================================================
# APP
# =========================================================

app = FastAPI(
    title=
        settings.app_name,

    version=
        settings.app_version,
)


# =========================================================
# FIREBASE / FCM
# =========================================================

@app.on_event("startup")
def initialize_firebase():
    """
    Inicializa Firebase Admin SDK al arrancar la API.

    Si Firebase está deshabilitado o la credencial no existe,
    FirebaseService.initialize() devuelve False sin impedir
    que FashionStore inicie.
    """

    FirebaseService.initialize()


# =========================================================
# SCHEDULER - EXPIRACIÓN AUTOMÁTICA
# =========================================================

expiration_scheduler = BackgroundScheduler(
    timezone="UTC",
)


@app.on_event("startup")
def start_background_scheduler():

    if settings.expiration_scheduler_enabled:
        expiration_scheduler.add_job(
            run_expiration_jobs,
            trigger="interval",
            minutes=settings.expiration_check_minutes,
            id="fashionstore-expiration",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    if settings.push_jobs_enabled:
        expiration_scheduler.add_job(
            run_push_delivery_jobs,
            trigger="interval",
            seconds=settings.push_job_interval_seconds,
            id="fashionstore-push-delivery",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    if settings.marketing_notification_jobs_enabled:
        expiration_scheduler.add_job(
            run_marketing_notification_jobs,
            trigger="interval",
            seconds=settings.marketing_campaign_job_interval_seconds,
            id="fashionstore-marketing-notifications",
            replace_existing=True,
            max_instances=1,
            coalesce=True,
        )

    has_enabled_jobs = any(
        (
            settings.expiration_scheduler_enabled,
            settings.push_jobs_enabled,
            settings.marketing_notification_jobs_enabled,
        )
    )

    if (
        has_enabled_jobs
        and not expiration_scheduler.running
    ):
        expiration_scheduler.start()


@app.on_event("shutdown")
def stop_expiration_scheduler():

    if expiration_scheduler.running:
        expiration_scheduler.shutdown(
            wait=False,
        )


# =========================================================
# CORS
# =========================================================

app.add_middleware(
    CORSMiddleware,

    allow_origins=[
        "http://localhost:4200",
    ],

    allow_credentials=
        True,

    allow_methods=[
        "*",
    ],

    allow_headers=[
        "*",
    ],
)


# =========================================================
# MÓDULO 1 - AUTENTICACIÓN, USUARIOS Y PERMISOS
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
    notifications_router
)

app.include_router(
    devices_router
)


# =========================================================
# MÓDULO 2 - SUCURSALES
# =========================================================

app.include_router(
    cities_router
)

app.include_router(
    branches_router
)

app.include_router(
    employee_branches_router
)


# =========================================================
# MÓDULO 3 - CATÁLOGO ADMINISTRATIVO
# =========================================================

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

app.include_router(
    cloudinary_test_router
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

# CU21 - Consultar existencias por sucursal
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

app.include_router(
    customer_merchandising_router
)

# CU26 - Consultar detalle de prenda
# CU27 - Consultar disponibilidad por sucursal
#
# Ambos están dentro del mismo router:
# customer_product_detail_router
app.include_router(
    customer_product_detail_router
)


# =========================================================
# MÓDULO 7 - RESERVAS
# =========================================================

# CU28 - Gestionar reservas
app.include_router(
    reservations_router
)

# =========================================================
# MÓDULO 8 - CARRITO
# =========================================================

# CU32 - Gestionar carrito de compras
app.include_router(
    carts_router
)


# =========================================================
# MÓDULO 9 - COMPRAS DIGITALES
# =========================================================

# CU33 - Gestionar compra digital
# CU34 - Consultar historial de compras
app.include_router(
    orders_router
)


# =========================================================
# MÓDULO 10 - VENTAS PRESENCIALES
# =========================================================

# CU35 - Gestionar venta presencial
app.include_router(
    sales_router
)

# CU36 - Gestionar pago en caja
app.include_router(
    cash_payments_router
)

# CU37 - Emitir comprobante
app.include_router(
    receipts_router
)


# =========================================================
# MÓDULO 11 - PAGOS ELECTRÓNICOS
# =========================================================

# CU38 - Gestionar pago electrónico
# CU39 - Consultar estado de pago
app.include_router(
    payments_router
)


# =========================================================
# MÓDULO 12 - REPORTES
# =========================================================

app.include_router(
    reports_router
)


# =========================================================
# DASHBOARD ADMINISTRATIVO
# =========================================================

app.include_router(
    dashboard_router
)


# =========================================================
# MÓDULO 13 - INTELIGENCIA ARTIFICIAL
# =========================================================

# CU43 - Obtener recomendaciones personalizadas de prendas
# CU44 - Consultar asistente inteligente de moda
# CU45 - Generar reporte inteligente bajo demanda
app.include_router(
    ai_router
)

# Asistente transaccional/navegacional del cliente
app.include_router(
    customer_assistant_router
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
