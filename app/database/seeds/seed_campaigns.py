"""Marketing de DEMOSTRACIÓN para los tres tenants.

Requiere etapas catalog y commerce completadas. No agenda envíos reales:
las campañas masivas se guardan CANCELLED y las notificaciones se crean
como bandeja interna del cliente, sin outbox FCM ni llamadas externas.
Idempotente, una transacción controlada por seed_multitenant.
"""
from datetime import datetime, date, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select, func
from app.database.seeds.seed_demo_config import DEMO_TENANTS
from app.models.product import Product
from app.models.collection import Collection
from app.models.product_collection import ProductCollection
from app.models.promotion import Promotion
from app.models.product_promotion import ProductPromotion
from app.models.notification_campaign import NotificationCampaign
from app.models.notification import Notification
from app.models.role import Role
from app.models.user import User
from app.models.sale import Sale
from app.models.order import Order

# Descuentos de demostración: no recalculan ventas/pedidos ya pagados.
# Fechas relativas permiten probar campañas vigentes/futuras/vencidas.
CAMPAIGNS = (
    ('Black Friday 2026', '30', -1, 14, 'Black Friday', 'BLACK_FRIDAY'),
    ('Cyber Monday', '20', 15, 24, 'Cyber Week', 'CYBER_MONDAY'),
    ('Navidad', '15', 25, 65, 'Regalos de Navidad', 'CHRISTMAS'),
    ('Liquidación de temporada', '25', -90, -30, 'Outlet de temporada', 'OUTLET'),
)

def seed_campaigns(db, tenant_ids):
    customer_role = db.scalar(select(Role).where(Role.name == 'CLIENTE'))
    if customer_role is None:
        raise RuntimeError('Falta rol CLIENTE; ejecuta primero staff')
    now = datetime.now(timezone.utc)
    report = {}
    for spec in DEMO_TENANTS:
        tid = tenant_ids[spec.slug]
        products = db.scalars(select(Product).where(Product.tenant_id == tid).order_by(Product.id)).all()
        customers = db.scalars(select(User).where(User.tenant_id == tid, User.role_id == customer_role.id).order_by(User.id)).all()
        if len(products) != spec.products or len(customers) != spec.customers:
            raise RuntimeError(f'{spec.slug}: requiere catalog y commerce completos')
        # Verifica historial comercial para validar que la carga sea útil en Flutter.
        sales = db.scalar(select(func.count(Sale.id)).where(Sale.tenant_id == tid))
        orders = db.scalar(select(func.count(Order.id)).where(Order.tenant_id == tid))
        if sales < spec.sales or orders < spec.orders:
            raise RuntimeError(f'{spec.slug}: faltan compras demo (sales={sales}, orders={orders})')
        created_promos = created_collections = created_notices = 0
        for index, (name, discount, start, end, collection_name, key) in enumerate(CAMPAIGNS):
            # Nuevos nombres exclusivos del demo, sin cambiar promociones comerciales existentes.
            promo = db.scalar(select(Promotion).where(Promotion.tenant_id == tid, Promotion.name == name))
            if promo is None:
                promo = Promotion(tenant_id=tid, name=name,
                    description=f'DEMO {spec.name} / {name} (no aplicar a compras históricas)',
                    discount_type='PERCENTAGE', discount_value=Decimal(discount),
                    start_at=now+timedelta(days=start), end_at=now+timedelta(days=end),
                    is_active=True)
                db.add(promo);db.flush();created_promos += 1
            elif promo.discount_type != 'PERCENTAGE' or promo.tenant_id != tid:
                raise RuntimeError(f'Promoción incompatible: {spec.slug}/{name}')
            coll = db.scalar(select(Collection).where(Collection.tenant_id == tid, Collection.name == collection_name))
            if coll is None:
                coll = Collection(tenant_id=tid, name=collection_name,
                    description=f'Colección DEMO {spec.name}',
                    launch_date=(now+timedelta(days=start)).date(), is_active=True)
                db.add(coll);db.flush();created_collections += 1
            # No vincular catálogo entero: muestras distintas por campaña y empresa.
            selected = [p for i,p in enumerate(products) if i % len(CAMPAIGNS) == index]
            for product in selected:
                if db.scalar(select(ProductPromotion.id).where(ProductPromotion.product_id == product.id, ProductPromotion.promotion_id == promo.id)) is None:
                    db.add(ProductPromotion(product_id=product.id,promotion_id=promo.id))
                if db.scalar(select(ProductCollection.id).where(ProductCollection.product_id == product.id, ProductCollection.collection_id == coll.id)) is None:
                    db.add(ProductCollection(product_id=product.id,collection_id=coll.id))
            db.flush()
            # Registro de campaña de auditoría deshabilitado. Evita que el job real
            # lo despache inmediatamente. Para envíos reales usar CRUD operativo.
            dedupe = f'DEMO-MARKETING-{tid}-{key}'
            campaign = db.scalar(select(NotificationCampaign).where(NotificationCampaign.dedupe_key == dedupe))
            if campaign is None:
                db.add(NotificationCampaign(campaign_type='PROMOTION', entity_id=promo.id,
                    event='PROMOTION_LAUNCHED',title=f'{spec.name}: {name}',
                    message=f'Descubre {name}: selección de productos con {discount}% de descuento.',
                    action_url=None,target_type='ALL_CUSTOMERS', status='CANCELLED',
                    scheduled_for=promo.start_at, attempt_count=0, dedupe_key=dedupe))
            elif campaign.entity_id != promo.id or campaign.status != 'CANCELLED':
                raise RuntimeError(f'Campaña ya existente con estado distinto o asociación incorrecta: {dedupe}')
            # Mensaje interno de prueba por cliente, no dispara push.
            # Solo anuncios vigentes o futuros, no la liquidación vencida.
            if end > 0:
                for customer in customers:
                    key_notice = f'DEMO-MARKETING-NOTICE-{tid}-{key}-{customer.id}'
                    existing = db.scalar(select(Notification.id).where(Notification.dedupe_key == key_notice))
                    if existing is None:
                        db.add(Notification(user_id=customer.id,type='PROMOTION',
                            event='PROMOTION_LAUNCHED',title=f'{spec.name}: {name}',
                            message=f'Campaña de prueba: {discount}% en productos seleccionados.',
                            entity_type='PROMOTION', entity_id=promo.id,
                            action_url=None,dedupe_key=key_notice,is_read=False))
                        created_notices += 1
        db.flush()
        report[spec.slug] = dict(promotions_new=created_promos,
            collections_new=created_collections, notifications_new=created_notices,
            customer_count=len(customers),campaigns_total=len(CAMPAIGNS))
    return report
