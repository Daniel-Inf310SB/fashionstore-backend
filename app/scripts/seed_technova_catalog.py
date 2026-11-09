"""Carga controlada y repetible del catálogo demo de TechNova.

Vista previa: python -m app.scripts.seed_technova_catalog
Aplicar:      python -m app.scripts.seed_technova_catalog --apply
"""
from __future__ import annotations

import argparse
from decimal import Decimal

from sqlalchemy import select, func

from app.database.session import SessionLocal
import app.models  # registra todas las relaciones ORM
from app.models.tenant import Tenant
from app.models.branch import Branch
from app.models.category import Category
from app.models.audience import Audience
from app.models.size import Size
from app.models.color import Color
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.inventory import Inventory

TENANT_SLUG = "technova-store"
BRANCH_NAME = "TechNova Centro"
# codigo, nombre, categoria, audiencia, precio
PRODUCTS = (
    ("TN-DEMO-001", "Camiseta básica TechNova", "Camisetas", "Unisex", "79.00"),
    ("TN-DEMO-002", "Polo algodón clásico", "Camisetas", "Hombre", "109.00"),
    ("TN-DEMO-003", "Camisa de lino casual", "Camisas", "Hombre", "179.00"),
    ("TN-DEMO-004", "Blusa cuello redondo", "Blusas", "Mujer", "119.00"),
    ("TN-DEMO-005", "Pantalón chino", "Pantalones", "Hombre", "199.00"),
    ("TN-DEMO-006", "Jean corte recto", "Pantalones", "Unisex", "209.00"),
    ("TN-DEMO-007", "Vestido casual", "Vestidos", "Mujer", "189.00"),
    ("TN-DEMO-008", "Chaqueta ligera", "Chaquetas", "Unisex", "249.00"),
    ("TN-DEMO-009", "Sudadera deportiva", "Deportiva", "Unisex", "169.00"),
    ("TN-DEMO-010", "Abrigo urbano", "Abrigos", "Unisex", "289.00"),
)
SIZES = ("S", "M", "L")
COLORS = ("Negro", "Blanco", "Azul")


def run(apply: bool) -> None:
    with SessionLocal() as db:
        try:
            tenant = db.scalar(select(Tenant).where(Tenant.slug == TENANT_SLUG))
            if not tenant or not tenant.is_active:
                raise RuntimeError("No existe el tenant activo 'technova-store'.")
            branch = db.scalar(select(Branch).where(Branch.name == BRANCH_NAME, Branch.tenant_id == tenant.id))
            if not branch or not branch.is_active:
                raise RuntimeError("La sucursal TechNova Centro no está activa o no pertenece a TechNova.")
            existing_products = db.scalar(select(func.count()).select_from(Product).where(Product.tenant_id == tenant.id)) or 0
            if existing_products and not all(db.scalar(select(Product.id).where(Product.tenant_id == tenant.id, Product.code == spec[0])) for spec in PRODUCTS):
                raise RuntimeError("TechNova ya tiene productos ajenos a este seed. Se detiene para evitar modificar su catálogo sin revisión.")
            sizes = {name: db.scalar(select(Size).where(Size.name == name, Size.is_active.is_(True))) for name in SIZES}
            colors = {name: db.scalar(select(Color).where(Color.name == name, Color.is_active.is_(True))) for name in COLORS}
            audiences = {name: db.scalar(select(Audience).where(Audience.name == name, Audience.is_active.is_(True))) for name in {spec[3] for spec in PRODUCTS}}
            missing = [f"talla {n}" for n, obj in sizes.items() if not obj] + [f"color {n}" for n, obj in colors.items() if not obj] + [f"público {n}" for n, obj in audiences.items() if not obj]
            if missing:
                raise RuntimeError("Faltan datos maestros (no se alterarán): " + ", ".join(missing))
            planned_categories = sorted({spec[2] for spec in PRODUCTS})
            categories = {name: db.scalar(select(Category).where(Category.tenant_id == tenant.id, Category.name == name)) for name in planned_categories}
            print(f"Tenant: {tenant.name} (ID {tenant.id}); sucursal: {branch.name} (ID {branch.id})")
            print(f"Productos actuales: {existing_products}; productos planificados: {len(PRODUCTS)}, variantes: 30")
            print("Categorías que faltan:", ", ".join(n for n, cat in categories.items() if cat is None) or "ninguna")
            if not apply:
                print("VISTA PREVIA: no se modificó PostgreSQL. Ejecuta con --apply para confirmar.")
                return
            for name, cat in categories.items():
                if cat is None:
                    cat = Category(tenant_id=tenant.id, name=name, description=f"Categoría demo {name}", is_active=True)
                    db.add(cat)
                    db.flush()
                    categories[name] = cat
            created_products = created_variants = created_inventory = 0
            for idx, (code, name, category, audience, price) in enumerate(PRODUCTS):
                product = db.scalar(select(Product).where(Product.tenant_id == tenant.id, Product.code == code))
                if product is None:
                    product = Product(tenant_id=tenant.id, code=code, name=name,
                                      description=f"Prenda de demostración {name} - TechNova Store",
                                      brand="TechNova", base_price=Decimal(price),
                                      category_id=categories[category].id, audience_id=audiences[audience].id,
                                      is_active=True)
                    db.add(product)
                    db.flush()
                    created_products += 1
                for j, (size_name, color_name) in enumerate(zip(SIZES, COLORS)):
                    size, color = sizes[size_name], colors[color_name]
                    variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id,
                                                                    ProductVariant.size_id == size.id,
                                                                    ProductVariant.color_id == color.id))
                    if variant is None:
                        variant = ProductVariant(product_id=product.id, size_id=size.id, color_id=color.id,
                                                 sku=f"{code}-{size_name}-{('NE','BL','AZ')[j]}",
                                                 additional_price=Decimal(j * 5), is_active=True)
                        db.add(variant)
                        db.flush()
                        created_variants += 1
                    inventory = db.scalar(select(Inventory).where(Inventory.branch_id == branch.id,
                                                                  Inventory.product_variant_id == variant.id))
                    if inventory is None:
                        db.add(Inventory(branch_id=branch.id, product_variant_id=variant.id,
                                         stock_quantity=10 + ((idx * 3 + j * 5) % 16), reserved_quantity=0,
                                         minimum_stock=3, reorder_point=5, is_active=True))
                        created_inventory += 1
            db.commit()
            print(f"APLICADO: {created_products} productos, {created_variants} variantes y {created_inventory} inventarios nuevos.")
            print("Los registros que ya existían no fueron alterados.")
        except Exception:
            db.rollback()
            raise


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed idempotente del catálogo demo TechNova")
    parser.add_argument("--apply", action="store_true", help="Confirmar cambios en PostgreSQL")
    args = parser.parse_args()
    run(args.apply)


if __name__ == "__main__":
    main()
