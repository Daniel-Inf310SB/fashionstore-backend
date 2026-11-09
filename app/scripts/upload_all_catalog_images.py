"""Carga masiva y segura de fotos locales a Cloudinary para productos y variantes SaaS.

CSV columnas: tenant_slug,product_code,kind,file_path,variant_sku,alt_text
kind: cover | gallery | variant
- cover: una portada por producto
- gallery: tantas fotos como se desee
- variant: una foto por SKU; para tallas del mismo color puede reutilizarse un archivo

Por defecto es simulación. --apply sube y registra imágenes, sin tocar productos,
precios, inventarios ni relaciones comerciales. No reemplaza fotografías reales.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import select
from app.database.session import SessionLocal
import app.models  # noqa: F401  registra relaciones ORM
from app.models.tenant import Tenant
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.product_image import ProductImage
from app.services.cloudinary_service import CloudinaryService
from app.core.cloudinary_config import configure_cloudinary

EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp"}
MAX_BYTES = 8 * 1024 * 1024
REQUIRED = {"tenant_slug", "product_code", "kind", "file_path", "variant_sku", "alt_text"}


@dataclass(frozen=True)
class Entry:
    tenant_slug: str
    product_code: str
    kind: str
    path: Path
    variant_sku: str
    alt_text: str


def placeholder(url: str | None) -> bool:
    if not url:
        return True
    parsed = urlparse(url)
    return parsed.hostname in {"picsum.photos", "fastly.picsum.photos"}


def load_csv(path: Path) -> list[Entry]:
    with path.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or not REQUIRED.issubset(reader.fieldnames):
            raise ValueError("CSV requiere: " + ", ".join(sorted(REQUIRED)))
        rows = []
        unique = set()
        for i, row in enumerate(reader, 2):
            slug = (row.get("tenant_slug") or "").strip()
            code = (row.get("product_code") or "").strip()
            kind = (row.get("kind") or "").strip().lower()
            sku = (row.get("variant_sku") or "").strip()
            rel = (row.get("file_path") or "").strip()
            if not slug or not code or kind not in {"cover", "gallery", "variant"} or not rel:
                raise ValueError(f"Fila {i}: tenant/producto/tipo/archivo inválidos")
            if kind == "variant" and not sku:
                raise ValueError(f"Fila {i}: variant requiere variant_sku")
            if kind != "variant" and sku:
                raise ValueError(f"Fila {i}: variant_sku solo corresponde a kind=variant")
            file = (path.parent / rel).resolve()
            if file.suffix.lower() not in EXTENSIONS or not file.is_file():
                raise ValueError(f"Fila {i}: archivo de imagen no encontrado: {file}")
            if not 0 < file.stat().st_size <= MAX_BYTES:
                raise ValueError(f"Fila {i}: archivo vacío o mayor que 8 MB: {file}")
            key = (slug, code, kind, sku if kind == "variant" else str(file))
            if key in unique:
                raise ValueError(f"Fila {i}: asociación duplicada {key}")
            unique.add(key)
            rows.append(Entry(slug, code, kind, file, sku, (row.get("alt_text") or "").strip()))
    return rows


def resolve(db, rows):
    products, variants = {}, {}
    result = []
    for row in rows:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == row.tenant_slug))
        if tenant is None:
            raise ValueError(f"Tenant inexistente: {row.tenant_slug}")
        pk = (tenant.id, row.product_code)
        if pk not in products:
            products[pk] = db.scalar(select(Product).where(
                Product.tenant_id == tenant.id, Product.code == row.product_code))
        product = products[pk]
        if product is None:
            raise ValueError(f"Producto inexistente en {row.tenant_slug}: {row.product_code}")
        variant = None
        if row.kind == "variant":
            key = (product.id, row.variant_sku)
            if key not in variants:
                variants[key] = db.scalar(select(ProductVariant).where(
                    ProductVariant.product_id == product.id,
                    ProductVariant.sku == row.variant_sku))
            variant = variants[key]
            if variant is None:
                raise ValueError(f"SKU no pertenece al producto/tenant: {row.variant_sku}")
        result.append((row, tenant, product, variant))
    # Una sola portada por producto; cada variante tiene una sola imagen.
    cover_keys = [(t.id, p.id) for r,t,p,v in result if r.kind == "cover"]
    if len(cover_keys) != len(set(cover_keys)):
        raise ValueError("Un producto tiene más de una portada en el CSV")
    return result


def existing_gallery(db, product, public_id):
    return db.scalar(select(ProductImage.id).where(
        ProductImage.product_id == product.id,
        ProductImage.cloudinary_public_id == public_id))


def run(csv_path: Path, apply: bool):
    rows = load_csv(csv_path)
    with SessionLocal() as db:
        plan = resolve(db, rows)  # Valida TODO antes de subir una sola imagen
        operations = []
        for row, tenant, product, variant in plan:
            old = (variant.image_url if variant else product.cover_image_url) if row.kind != "gallery" else None
            if row.kind != "gallery" and not placeholder(old):
                action = "OMITIR (ya tiene foto real)"
            else:
                action = "SUBIR"
            operations.append((row, tenant, product, variant, action))
        stats = Counter(action for *_, action in operations)
        print(f"Filas: {len(rows)}; a subir: {stats['SUBIR']}; preservadas: {stats['OMITIR (ya tiene foto real)']}")
        for row, tenant, product, variant, action in operations:
            print(f"{action}: {row.tenant_slug}/{row.product_code} {row.kind} {row.variant_sku} => {row.path.name}")
        if not apply:
            print("SIMULACIÓN: no se ha subido ninguna imagen ni modificado PostgreSQL.")
            return

        configure_cloudinary()
        done = 0
        for row, tenant, product, variant, action in operations:
            if action != "SUBIR":
                continue
            # Un commit por asociación hace reanudable el proceso sin perder lo ya guardado.
            uploaded = None
            try:
                # Revalidar en la transacción antes de escribir para evitar reemplazos accidentales.
                db.refresh(product)
                if variant:
                    db.refresh(variant)
                current = (variant.image_url if variant else product.cover_image_url) if row.kind != "gallery" else None
                if row.kind != "gallery" and not placeholder(current):
                    print(f"OMITIDO tras revalidar: {row.product_code} {row.kind} {row.variant_sku}")
                    continue
                digest = hashlib.sha256(row.path.read_bytes()).hexdigest()[:16]
                folder = f"fashionstore/tenants/{tenant.id}/products/{product.id}"
                if variant:
                    folder += "/variants"
                public_name = f"{row.kind}-{variant.id if variant else product.id}-{digest}"
                expected_public_id = f"{folder}/{public_name}"
                # En una repetición, no crear otra galería con el mismo archivo.
                if row.kind == "gallery" and existing_gallery(db, product, expected_public_id):
                    print(f"YA EXISTE: {row.product_code} {row.path.name}")
                    continue
                with row.path.open("rb") as stream:
                    uploaded = CloudinaryService.upload_image(stream, folder=folder, public_id=public_name)
                if row.kind == "cover":
                    product.cover_image_url = uploaded["url"]
                    product.cover_image_public_id = uploaded["public_id"]
                    # Conservar las galerías actuales y añadir la portada solo si no existe.
                    if not existing_gallery(db, product, uploaded["public_id"]):
                        db.add(ProductImage(product_id=product.id,
                            image_url=uploaded["url"], cloudinary_public_id=uploaded["public_id"],
                            alt_text=row.alt_text or product.name, is_primary=True,
                            is_active=True, sort_order=0))
                elif row.kind == "gallery":
                    if not existing_gallery(db, product, uploaded["public_id"]):
                        db.add(ProductImage(product_id=product.id,
                            image_url=uploaded["url"], cloudinary_public_id=uploaded["public_id"],
                            alt_text=row.alt_text or product.name, is_primary=False,
                            is_active=True, sort_order=1000 + done))
                else:
                    variant.image_url = uploaded["url"]
                    variant.cloudinary_public_id = uploaded["public_id"]
                db.commit()
                done += 1
                print(f"OK {done}: {row.product_code} {row.kind} {row.variant_sku}")
            except Exception:
                db.rollback()
                if uploaded:
                    try:
                        CloudinaryService.delete_image(uploaded["public_id"])
                    except Exception:
                        print("AVISO: revisar manualmente imagen huérfana en Cloudinary")
                raise
        print(f"FINALIZADO: {done} asociaciones aplicadas.")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--manifest", type=Path, required=True)
    ap.add_argument("--apply", action="store_true", help="Confirma subida y escritura en PostgreSQL")
    args = ap.parse_args()
    run(args.manifest.resolve(), args.apply)


if __name__ == "__main__":
    main()
