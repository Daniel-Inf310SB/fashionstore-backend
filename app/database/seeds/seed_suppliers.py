"""Bloque 3: proveedores, productos abastecidos y disponibilidad, con aislamiento."""
from decimal import Decimal
from sqlalchemy import select
from app.database.seeds.seed_demo_config import DEMO_TENANTS
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.supplier_availability import SupplierAvailability
from app.models.product_variant import ProductVariant


def seed_suppliers(db, tenant_ids, catalog):
    counts={}
    for spec in DEMO_TENANTS:
        tid=tenant_ids[spec.slug]
        products=catalog[spec.slug]
        suppliers=[]
        for i in range(spec.suppliers):
            nit=f'900{tid:03d}{i+1:05d}'
            s=db.scalar(select(Supplier).where(Supplier.tenant_id==tid,Supplier.nit==nit))
            if s is None:
                s=Supplier(tenant_id=tid,name=f'{spec.name} Distribuidor {i+1:02d}',business_name=f'Distribuciones {spec.name} {i+1:02d}',nit=nit,phone=f'700{tid:02d}{i+1:04d}',email=f'proveedor{i+1}@{spec.slug.replace("-", "")}.test',address='Santa Cruz, Bolivia',contact_name=f'Contacto {i+1}',is_active=True)
                db.add(s);db.flush()
            suppliers.append(s)
        linked=0
        for i,p in enumerate(products):
            # Cada producto queda vinculado por lo menos a un proveedor; cada quinto, a dos.
            candidates=[suppliers[i%len(suppliers)]]
            if i%5==0: candidates.append(suppliers[(i+1)%len(suppliers)])
            for supplier in {s.id:s for s in candidates}.values():
                if supplier.tenant_id != p.tenant_id: raise RuntimeError('Cruce de tenants en proveedor/producto')
                sp=db.scalar(select(SupplierProduct).where(SupplierProduct.supplier_id==supplier.id,SupplierProduct.product_id==p.id))
                if sp is None:
                    sp=SupplierProduct(supplier_id=supplier.id,product_id=p.id,supplier_code=f'SUP-{supplier.id}-{p.code}',purchase_price=(Decimal(p.base_price)*Decimal('0.58')).quantize(Decimal('.01')),minimum_order_quantity=5,lead_time_days=3,is_active=True)
                    db.add(sp);db.flush()
                linked+=1
                for v in db.scalars(select(ProductVariant).where(ProductVariant.product_id==p.id)).all():
                    av=db.scalar(select(SupplierAvailability).where(SupplierAvailability.supplier_product_id==sp.id,SupplierAvailability.product_variant_id==v.id))
                    if av is None:
                        qty=50+(i%6)*10
                        db.add(SupplierAvailability(supplier_product_id=sp.id,product_variant_id=v.id,available_quantity=qty,status='AVAILABLE',purchase_price=sp.purchase_price))
        counts[spec.slug]={'suppliers':len(suppliers),'products':len(products),'links':linked}
    db.flush()
    return counts
