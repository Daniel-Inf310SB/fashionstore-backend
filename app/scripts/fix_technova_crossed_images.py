"""Corrige SOLO las imágenes cruzadas TN-DEMO-010 / TN-DEMO-004 en TechNova.

Sin --apply: simulación. No sube ni borra archivos en Cloudinary.
"""
import argparse
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.tenant import Tenant
from app.models.product import Product
from app.models.product_image import ProductImage


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--apply', action='store_true', help='Intercambia portadas y miniaturas en una transacción')
    args = parser.parse_args()
    with SessionLocal() as db:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == 'technova-store'))
        if tenant is None:
            raise RuntimeError('No existe el tenant technova-store')
        products = {}
        for code in ('TN-DEMO-010', 'TN-DEMO-004'):
            product = db.scalar(select(Product).where(Product.tenant_id == tenant.id, Product.code == code))
            if product is None:
                raise RuntimeError(f'No existe {code} en TechNova')
            if not product.cover_image_url or 'res.cloudinary.com/' not in product.cover_image_url or not product.cover_image_public_id:
                raise RuntimeError(f'{code} no tiene portada Cloudinary; se detiene para no alterar fotos inesperadas')
            products[code] = product
        abrigo, blusa = products['TN-DEMO-010'], products['TN-DEMO-004']
        img_a = db.scalar(select(ProductImage).where(ProductImage.product_id == abrigo.id, ProductImage.cloudinary_public_id == abrigo.cover_image_public_id))
        img_b = db.scalar(select(ProductImage).where(ProductImage.product_id == blusa.id, ProductImage.cloudinary_public_id == blusa.cover_image_public_id))
        if img_a is None or img_b is None or img_a.id == img_b.id:
            raise RuntimeError('No se localizaron ambas miniaturas Cloudinary; se aborta sin modificar datos')
        print('PLAN — TechNova Store:')
        print(f'  {abrigo.code} ({abrigo.name}) recibirá la portada Cloudinary que está en {blusa.code}')
        print(f'  {blusa.code} ({blusa.name}) recibirá la portada Cloudinary que está en {abrigo.code}')
        print('  Se corregirán también las dos miniaturas. Camisa, precios, stock y variantes no se modifican.')
        if not args.apply:
            print('SIMULACIÓN — sin cambios. Para aplicar, agrega --apply')
            return
        abrigo.cover_image_url, blusa.cover_image_url = blusa.cover_image_url, abrigo.cover_image_url
        abrigo.cover_image_public_id, blusa.cover_image_public_id = blusa.cover_image_public_id, abrigo.cover_image_public_id
        img_a.product_id, img_b.product_id = blusa.id, abrigo.id
        img_a.alt_text, img_b.alt_text = 'Blusa cuello redondo (ilustrativa)', 'Abrigo urbano (ilustrativa)'
        db.commit()
        print('CORREGIDO — portadas y miniaturas intercambiadas; sin nuevas subidas Cloudinary')


if __name__ == '__main__':
    main()
