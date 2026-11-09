"""Carga fotografías locales en Cloudinary y sustituye solo portadas Picsum de un tenant.

CSV requerido: code,file_path (relativos al CSV). Opcional: alt_text.
Sin --apply: solo simulación, no realiza subidas ni escrituras.
"""
from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy import select

from app.core.cloudinary_config import configure_cloudinary
from app.database.session import SessionLocal
from app.models.product import Product
from app.models.product_image import ProductImage
from app.models.tenant import Tenant
from app.services.cloudinary_service import CloudinaryService

SUPPORTED = {'.jpg', '.jpeg', '.png', '.webp'}
MAX_BYTES = 5 * 1024 * 1024


def is_demo_url(value: str | None) -> bool:
    if not value:
        return True
    from urllib.parse import urlparse
    parsed = urlparse(value)
    return parsed.scheme == 'https' and parsed.hostname in {'picsum.photos', 'fastly.picsum.photos'}


@dataclass(frozen=True)
class Row:
    code: str
    path: Path
    alt: str


def read_rows(csv_path: Path) -> list[Row]:
    with csv_path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle)
        if not reader.fieldnames or not {'code', 'file_path'}.issubset(reader.fieldnames):
            raise ValueError('CSV debe contener code,file_path')
        rows = []
        codes = set()
        for item in reader:
            code = (item.get('code') or '').strip()
            name = (item.get('file_path') or '').strip()
            if not code or not name or code in codes:
                raise ValueError(f'Código o archivo inválido/duplicado: {code!r}')
            codes.add(code)
            filename = (csv_path.parent / name).resolve()
            if filename.suffix.lower() not in SUPPORTED or not filename.is_file():
                raise ValueError(f'Falta archivo JPG/PNG/WEBP: {filename}')
            if not 0 < filename.stat().st_size <= MAX_BYTES:
                raise ValueError(f'Tamaño inválido (máx 5 MB): {filename}')
            rows.append(Row(code, filename, (item.get('alt_text') or '').strip()))
    return rows


def make_plan(db, slug: str, rows: list[Row]):
    tenant = db.scalar(select(Tenant).where(Tenant.slug == slug))
    if tenant is None:
        raise ValueError(f'Tenant desconocido: {slug}')
    targets = []
    for row in rows:
        product = db.scalar(select(Product).where(Product.tenant_id == tenant.id, Product.code == row.code))
        if product is None:
            raise ValueError(f'Producto no encontrado en {slug}: {row.code}')
        if not is_demo_url(product.cover_image_url):
            print(f'SALTADO {row.code}: ya tiene portada real')
            continue
        targets.append((tenant, product, row))
    return targets


def run(slug: str, manifest: Path, apply: bool) -> None:
    rows = read_rows(manifest)
    with SessionLocal() as db:
        targets = make_plan(db, slug, rows)
        print(f"{'APLICAR' if apply else 'SIMULACIÓN'}: tenant={slug}, fotos={len(rows)}, portadas_para_actualizar={len(targets)}")
        for _tenant, product, row in targets:
            print(f'  {product.code} — {product.name}: {row.path.name}')
        if not apply:
            return
        configure_cloudinary()
        for tenant, product, row in targets:
            uploaded = None
            try:
                with row.path.open('rb') as stream:
                    uploaded = CloudinaryService.upload_image(stream, folder=f'fashionstore/tenants/{tenant.id}/products/{product.id}')
                # Recuperar cualquier galería antigua vinculada al placeholder principal,
                # sin eliminar fotografías reales ni recursos de Cloudinary existentes.
                old_cover = product.cover_image_url
                if not is_demo_url(old_cover):
                    raise RuntimeError('La portada cambió durante la operación; se omite el producto')
                old_demo_images = list(db.scalars(select(ProductImage).where(ProductImage.product_id == product.id)).all())
                for old in old_demo_images:
                    if is_demo_url(old.image_url) and old.cloudinary_public_id is None:
                        db.delete(old)
                product.cover_image_url = uploaded['url']
                product.cover_image_public_id = uploaded['public_id']
                db.add(ProductImage(product_id=product.id, image_url=uploaded['url'], cloudinary_public_id=uploaded['public_id'], alt_text=row.alt or product.name, is_primary=True, is_active=True, sort_order=0))
                db.commit()
                print(f'  OK {product.code}: portada Cloudinary guardada')
            except Exception:
                db.rollback()
                if uploaded:
                    try:
                        CloudinaryService.delete_image(uploaded['public_id'])
                    except Exception:
                        print(f"AVISO: borrar manualmente Cloudinary public_id={uploaded['public_id']}")
                raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--tenant', required=True)
    parser.add_argument('--manifest', required=True, type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    run(args.tenant, args.manifest.resolve(), args.apply)


if __name__ == '__main__':
    main()
