"""Asocia portadas/galerías a productos SaaS sin tocar datos comerciales.

Por defecto solo simula. Los vínculos del manifiesto deben corresponder a imágenes
que el usuario tiene permiso de usar. No sube contenido a Cloudinary.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from urllib.parse import quote, urlparse

from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.tenant import Tenant


@dataclass(frozen=True)
class ImageEntry:
    url: str
    public_id: str | None = None
    alt: str | None = None


def valid_url(url: str) -> bool:
    parsed = urlparse(url)
    return parsed.scheme == 'https' and bool(parsed.netloc) and len(url) <= 500


def load_manifest(path: str) -> dict[str, list[ImageEntry]]:
    result: dict[str, list[ImageEntry]] = {}
    with open(path, encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {'code', 'image_url'}.issubset(reader.fieldnames):
            raise ValueError('CSV requiere columnas code,image_url (opcionales: public_id,alt_text)')
        for row in reader:
            code = (row.get('code') or '').strip()
            url = (row.get('image_url') or '').strip()
            if not code or not valid_url(url):
                raise ValueError(f'Código/URL inválidos en manifiesto: {code!r}')
            result.setdefault(code, []).append(ImageEntry(url, (row.get('public_id') or '').strip() or None, (row.get('alt_text') or '').strip() or None))
    return result


def entries_for(product: Product, manifest: dict[str, list[ImageEntry]], demo: bool, count: int) -> list[ImageEntry]:
    if manifest:
        return manifest.get(product.code, [])
    if not demo:
        return []
    # Picsum genera fotografías aleatorias, NO fotografías reales de las prendas.
    return [ImageEntry(f'https://picsum.photos/seed/{quote(f"fs-demo-{product.tenant_id}-{product.id}-{i}", safe="")}/800/1000', None, f'Imagen ilustrativa de demostración: {product.name}') for i in range(1, count + 1)]


def seed(db, tenant_slug: str, manifest: dict[str, list[ImageEntry]], demo: bool, count: int, apply: bool, limit: int | None) -> dict[str, int]:
    tenant = db.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
    if tenant is None:
        raise ValueError(f'No existe empresa con slug {tenant_slug!r}')
    products = list(db.scalars(select(Product).where(Product.tenant_id == tenant.id).order_by(Product.id).limit(limit)).all())
    stats = dict(products=len(products), cover_created=0, gallery_created=0, untouched=0)
    for product in products:
        entries = entries_for(product, manifest, demo, count)
        if not entries:
            stats['untouched'] += 1
            continue
        existing = list(db.scalars(select(ProductImage).where(ProductImage.product_id == product.id)).all())
        urls = {im.image_url for im in existing}
        existing_primary = any(im.is_primary and im.is_active for im in existing)
        has_cover = bool(product.cover_image_url)
        changed = False
        for index, entry in enumerate(entries):
            if not valid_url(entry.url):
                raise ValueError(f'URL inválida para {product.code}')
            if entry.url not in urls:
                stats['gallery_created'] += 1
                changed = True
                if apply:
                    db.add(ProductImage(product_id=product.id, image_url=entry.url, cloudinary_public_id=entry.public_id,
                                        alt_text=entry.alt or f'{product.name} — imagen {index + 1}',
                                        sort_order=len(existing) + index + 1,
                                        is_primary=not existing_primary and not has_cover and index == 0,
                                        is_active=True))
                urls.add(entry.url)
            if index == 0 and not has_cover:
                stats['cover_created'] += 1
                changed = True
                if apply:
                    product.cover_image_url = entry.url
                    product.cover_image_public_id = entry.public_id
        if not changed:
            stats['untouched'] += 1
    if apply:
        db.commit()
    return stats


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tenant', required=True, help='Slug de empresa, p.ej. technova-store')
    choices = parser.add_mutually_exclusive_group(required=True)
    choices.add_argument('--manifest', help='CSV con code,image_url,public_id,alt_text')
    choices.add_argument('--demo-placeholders', action='store_true', help='URLs Picsum aleatorias SOLO de demostración')
    parser.add_argument('--images-per-product', type=int, default=3)
    parser.add_argument('--limit', type=int, default=None)
    parser.add_argument('--apply', action='store_true', help='Sin esto, simulación sin escribir en BD')
    args = parser.parse_args()
    if not 1 <= args.images_per_product <= 5:
        parser.error('--images-per-product debe estar entre 1 y 5')
    if args.limit is not None and args.limit < 1:
        parser.error('--limit debe ser positivo')
    manifest = load_manifest(args.manifest) if args.manifest else {}
    with SessionLocal() as db:
        try:
            result = seed(db, args.tenant, manifest, args.demo_placeholders, args.images_per_product, args.apply, args.limit)
            print(('APLICADO' if args.apply else 'SIMULACIÓN'), result)
        except Exception:
            db.rollback()
            raise


if __name__ == '__main__':
    main()
