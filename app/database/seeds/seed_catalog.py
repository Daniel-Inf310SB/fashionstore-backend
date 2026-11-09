"""Bloque 3: catálogo multiempresa, idempotente y sin commits internos."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from sqlalchemy import select
from app.database.seeds.seed_demo_config import DEMO_TENANTS
from app.models.category import Category
from app.models.audience import Audience
from app.models.size import Size
from app.models.color import Color
from app.models.season import Season
from app.models.collection import Collection
from app.models.promotion import Promotion
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.product_season import ProductSeason
from app.models.product_collection import ProductCollection
from app.models.product_promotion import ProductPromotion

CATEGORIES = ('Camisetas', 'Pantalones', 'Vestidos', 'Chaquetas', 'Calzado', 'Deportiva', 'Accesorios', 'Abrigos')
AUDIENCES = ('Mujer', 'Hombre', 'Unisex')
SIZES = ('S', 'M', 'L')
COLORS = (('Negro','#111111'), ('Blanco','#FFFFFF'), ('Azul','#2563EB'))
SEASONS = ('Todo el año', 'Primavera-Verano', 'Otoño-Invierno')
COLLECTIONS = ('Esenciales', 'Urbana', 'Temporada')
ITEMS = ('Camiseta básica','Camiseta oversize','Camiseta estampada','Polo casual','Blusa elegante',
         'Top deportivo','Camisa Oxford','Camisa de lino','Jean recto','Jean slim','Pantalón chino',
         'Pantalón cargo','Jogger cómodo','Short casual','Falda plisada','Vestido midi',
         'Vestido corto','Chaqueta denim','Chaqueta bomber','Sudadera con capucha',
         'Suéter tejido','Abrigo ligero','Zapatilla urbana','Zapatilla running',
         'Sandalia casual','Botín clásico','Mochila urbana','Gorra básica','Conjunto deportivo','Legging deportivo')

def get_or_create(db, cls, criteria, values):
    stmt = select(cls).filter_by(**criteria)
    obj = db.scalar(stmt)
    if obj is None:
        obj = cls(**criteria, **values)
        db.add(obj)
        db.flush()
    return obj

def seed_catalog(db, tenant_ids):
    audiences = {n: get_or_create(db,Audience,{'name':n},{'description':'Público '+n,'is_active':True}) for n in AUDIENCES}
    sizes = {n: get_or_create(db,Size,{'name':n},{'sort_order':i+1,'is_active':True}) for i,n in enumerate(SIZES)}
    colors = {n: get_or_create(db,Color,{'name':n},{'hex_code':hexcode,'is_active':True}) for n,hexcode in COLORS}
    seasons = {n: get_or_create(db,Season,{'name':n},{'is_active':True}) for n in SEASONS}
    prefixes = {"fashionstore": "FS", "urban-style-demo": "US", "technova-store": "TN"}
    brands = {"fashionstore": "FashionStore", "urban-style-demo": "Urban Style", "technova-store": "TechNova"}
    result={}
    now=datetime.now(timezone.utc)
    for spec in DEMO_TENANTS:
        tid=tenant_ids[spec.slug]
        categories = {n:get_or_create(db,Category,{'tenant_id':tid,'name':n},{'description':f'Categoría {n}','is_active':True}) for n in CATEGORIES}
        collections = {n:get_or_create(db,Collection,{'tenant_id':tid,'name':n},{'description':f'Colección {n}','is_active':True}) for n in COLLECTIONS}
        promo = get_or_create(db,Promotion,{'tenant_id':tid,'name':'Bienvenida 10%'},{'description':'Campaña de demostración','discount_type':'PERCENTAGE','discount_value':Decimal('10.00'),'start_at':now-timedelta(days=1),'end_at':now+timedelta(days=365),'is_active':True})
        products=[]
        for i in range(spec.products):
            cname=CATEGORIES[i%len(CATEGORIES)]
            base=ITEMS[i%len(ITEMS)]
            code=f"{prefixes[spec.slug]}-P{i+1:04d}"
            product=get_or_create(db,Product,{'tenant_id':tid,'code':code},{'name':f'{base} {i//len(ITEMS)+1:02d}','description':f'{base}, colección de demostración {spec.name}','brand':brands[spec.slug],'base_price':Decimal(70+(i%18)*15),'category_id':categories[cname].id,'audience_id':audiences[AUDIENCES[i%3]].id,'is_active':True})
            if product.category_id != categories[cname].id: raise RuntimeError(f'Categoría incongruente para {code}')
            products.append(product)
            for j in range(spec.variants_per_product):
                size=SIZES[j%len(SIZES)]; color=list(colors)[(i+j)%len(colors)]
                sku=f'{code}-{size}-{color[:2].upper()}'
                variant=db.scalar(select(ProductVariant).where(ProductVariant.product_id==product.id,ProductVariant.size_id==sizes[size].id,ProductVariant.color_id==colors[color].id))
                if variant is None:
                    if db.scalar(select(ProductVariant).where(ProductVariant.sku==sku)) is not None: raise RuntimeError(f'SKU ya ocupado: {sku}')
                    db.add(ProductVariant(product_id=product.id,size_id=sizes[size].id,color_id=colors[color].id,sku=sku,additional_price=Decimal(j*5),is_active=True))
            season=seasons[SEASONS[i%len(SEASONS)]]
            collection=collections[COLLECTIONS[i%len(COLLECTIONS)]]
            get_or_create(db,ProductSeason,{'product_id':product.id,'season_id':season.id},{})
            get_or_create(db,ProductCollection,{'product_id':product.id,'collection_id':collection.id},{})
            if i%5==0:
                get_or_create(db,ProductPromotion,{'product_id':product.id,'promotion_id':promo.id},{})
        db.flush()
        result[spec.slug]=products
    return result
