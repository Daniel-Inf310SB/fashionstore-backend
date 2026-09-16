from __future__ import annotations

from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.size import Size
from app.models.color import Color
from app.database.seeds.seed_demo_config import VARIANTS_PER_PRODUCT


def seed_product_variants(db: Session) -> None:
    print(f"🌱 Seed catálogo: {VARIANTS_PER_PRODUCT} variantes por producto, sin combinatoria talla×color...")
    products = list(db.scalars(select(Product).where(Product.is_active.is_(True)).order_by(Product.id)).all())
    sizes = list(db.scalars(select(Size).where(Size.is_active.is_(True)).order_by(Size.sort_order, Size.id)).all())
    colors = list(db.scalars(select(Color).where(Color.is_active.is_(True)).order_by(Color.id)).all())
    if not products or not sizes or not colors:
        raise RuntimeError("Faltan productos, tallas o colores para crear variantes.")

    created = updated = 0
    for p_index, product in enumerate(products):
        # Tres pares talla/color distintos. NO se genera el producto cartesiano.
        for offset in range(VARIANTS_PER_PRODUCT):
            size = sizes[(p_index + offset * 2) % len(sizes)]
            color = colors[(p_index * 2 + offset * 3) % len(colors)]
            sku = f"{product.code}-{size.name}-{color.name[:3].upper()}"
            variant = db.scalar(select(ProductVariant).where(ProductVariant.product_id == product.id, ProductVariant.size_id == size.id, ProductVariant.color_id == color.id))
            add_price = Decimal("0.00") if offset < 2 else Decimal("10.00")
            image_url = f"https://picsum.photos/seed/{sku.lower().replace(' ', '-')}/800/1000"
            if variant is None:
                variant = ProductVariant(product_id=product.id, size_id=size.id, color_id=color.id, sku=sku, additional_price=add_price, image_url=image_url, is_active=True)
                db.add(variant)
                created += 1
            else:
                variant.sku = sku
                variant.additional_price = add_price
                variant.image_url = image_url
                variant.is_active = True
                updated += 1
    db.flush()
    print(f"✅ Variantes listas: {created} creadas, {updated} actualizadas ({len(products) * VARIANTS_PER_PRODUCT} esperadas).")
