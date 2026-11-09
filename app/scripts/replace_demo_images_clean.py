"""Sustituir SOLO las ilustraciones DEMO cargadas previamente usando nuestro script.
Simula por defecto, identifica cada imagen por public_id y hash de la original.
No elimina originales de Cloudinary; conserva CSV de auditoría reversible.
"""
import argparse, csv, hashlib, json
from pathlib import Path
from datetime import datetime,timezone
from sqlalchemy import select
from app.database.session import SessionLocal
import app.models
from app.models.tenant import Tenant
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.product_image import ProductImage
from app.core.cloudinary_config import configure_cloudinary
from app.services.cloudinary_service import CloudinaryService


def run(root, apply=False, tenant_slug=None, limit=None):
    manifest=root/'imagenes.csv'
    rows=list(csv.DictReader(manifest.open(encoding='utf-8-sig',newline='')))
    old_hashes=json.loads((root/'hashes_originales.json').read_text(encoding='utf-8'))
    report_path=root/'registro_reemplazos.csv'
    planned=[]
    with SessionLocal() as db:
        for r in rows:
            if tenant_slug and r['tenant_slug']!=tenant_slug:continue
            f=root/r['file_path']
            if not f.is_file():raise FileNotFoundError(f)
            tenant=db.scalar(select(Tenant).where(Tenant.slug==r['tenant_slug']))
            if tenant is None:raise ValueError(f"Tenant desconocido: {r['tenant_slug']}")
            product=db.scalar(select(Product).where(Product.tenant_id==tenant.id,Product.code==r['product_code']))
            if product is None:raise ValueError(f"Producto desconocido: {r['product_code']}")
            variant=None
            if r['kind']=='variant':
                variant=db.scalar(select(ProductVariant).where(ProductVariant.product_id==product.id,ProductVariant.sku==r['variant_sku']))
                if variant is None:raise ValueError(f"Variante desconocida: {r['variant_sku']}")
            if r['kind'] not in ('cover','variant'):raise ValueError('Solo cover y variant')
            old_url=variant.image_url if variant else product.cover_image_url
            old_pid=variant.cloudinary_public_id if variant else product.cover_image_public_id
            digest=old_hashes[r['file_path']]
            expected_suffix=f"/{r['kind']}-{variant.id if variant else product.id}-{digest}"
            if not old_pid or not old_pid.endswith(expected_suffix):
                status='OMITIR: fotografía distinta o modificada por admin'
            else:
                status='REEMPLAZAR DEMO'
            planned.append((r,f,tenant.id,product.id,variant.id if variant else None,old_url,old_pid,status))
        print(f'Asociaciones consideradas: {len(planned)}; reemplazables: {sum(p[7]=="REEMPLAZAR DEMO" for p in planned)}; preservadas: {sum(p[7]!="REEMPLAZAR DEMO" for p in planned)}')
        for r,f,tid,pid,vid,url,old_id,status in planned[:10]:print(status,r['tenant_slug'],r['product_code'],r['kind'],r['variant_sku'])
        if not apply:
            print('SIMULACIÓN: no se modificó nada; usa --apply cuando hayas hecho respaldo.');return
        configure_cloudinary()
        # report is appended before/after each successful commit.
        with report_path.open('a',encoding='utf-8-sig',newline='') as fh:
            writer=csv.writer(fh)
            if fh.tell()==0:writer.writerow(['fecha','tenant','producto','tipo','sku','old_url','old_public_id','new_url','new_public_id'])
            done=0
            for r,f,tid,pid,vid,old_url,old_pid,status in planned:
                if limit is not None and done>=limit:break
                if status!='REEMPLAZAR DEMO':continue
                product=db.get(Product,pid)
                variant=db.get(ProductVariant,vid) if vid else None
                current_pid=variant.cloudinary_public_id if variant else product.cover_image_public_id
                if current_pid!=old_pid:
                    print('OMITIDA por cambio concurrente:',r['product_code'],r['variant_sku']);continue
                uploaded=None
                try:
                    folder=f'fashionstore/tenants/{tid}/products/{pid}' + ('/variants' if variant else '')
                    with f.open('rb') as stream:
                        uploaded=CloudinaryService.upload_image(stream,folder=folder)
                    if variant:
                        variant.image_url=uploaded['url'];variant.cloudinary_public_id=uploaded['public_id']
                    else:
                        product.cover_image_url=uploaded['url'];product.cover_image_public_id=uploaded['public_id']
                        for gallery in db.scalars(select(ProductImage).where(ProductImage.product_id==pid,ProductImage.cloudinary_public_id==old_pid)).all():
                            gallery.image_url=uploaded['url'];gallery.cloudinary_public_id=uploaded['public_id']
                    db.commit()
                    writer.writerow([datetime.now(timezone.utc).isoformat(),r['tenant_slug'],r['product_code'],r['kind'],r['variant_sku'],old_url,old_pid,uploaded['url'],uploaded['public_id']]);fh.flush()
                    done+=1
                    print('OK',done,r['product_code'],r['kind'],r['variant_sku'])
                except Exception:
                    db.rollback()
                    if uploaded:
                        try:CloudinaryService.delete_image(uploaded['public_id'])
                        except Exception:print('AVISO: imagen huérfana:',uploaded['public_id'])
                    raise
            print('REEMPLAZOS APLICADOS:',done,'Registro:',report_path)

if __name__=='__main__':
    ap=argparse.ArgumentParser()
    ap.add_argument('--carpeta',type=Path,default=Path('imagenes_limpias'))
    ap.add_argument('--tenant')
    ap.add_argument('--limit',type=int)
    ap.add_argument('--apply',action='store_true')
    a=ap.parse_args()
    run(a.carpeta.resolve(),a.apply,a.tenant,a.limit)
