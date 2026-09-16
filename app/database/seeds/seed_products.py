from __future__ import annotations

from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.audience import Audience
from app.models.product import Product
from app.database.seeds.seed_demo_config import PRODUCT_COUNT

CATEGORY_CONFIG = [
    ("Poleras", "POL", 89, ["Essential", "Oversize", "Urban", "Classic", "Street"]),
    ("Camisas", "CAM", 139, ["Oxford", "Linen", "Smart", "Classic"]),
    ("Pantalones", "PAN", 169, ["Cargo", "Chino", "Relaxed", "Formal"]),
    ("Jeans", "JEA", 189, ["Straight", "Slim", "Wide", "Classic"]),
    ("Vestidos", "VES", 219, ["Midi", "Summer", "Elegance", "Night"]),
    ("Chaquetas", "CHA", 279, ["Bomber", "Denim", "Urban", "Classic"]),
    ("Shorts", "SHO", 119, ["Summer", "Cargo", "Sport", "Basic"]),
    ("Faldas", "FAL", 149, ["Midi", "Denim", "Pleated", "Classic"]),
]


def seed_products(db: Session) -> None:
    print(f"🌱 Seed catálogo: {PRODUCT_COUNT} productos...")
    categories = {x.name: x for x in db.scalars(select(Category)).all()}
    audiences = {x.name: x for x in db.scalars(select(Audience)).all()}
    if not categories or not audiences:
        raise RuntimeError("Ejecuta seed_catalog_master antes de seed_products.")

    audience_cycle = ["Hombre", "Mujer", "Unisex"]
    created = updated = 0
    for index in range(1, PRODUCT_COUNT + 1):
        category_name, prefix, base, styles = CATEGORY_CONFIG[(index - 1) % len(CATEGORY_CONFIG)]
        category = categories[category_name]
        audience_name = "Mujer" if category_name in {"Vestidos", "Faldas"} else audience_cycle[(index - 1) % len(audience_cycle)]
        audience = audiences[audience_name]
        style = styles[(index - 1) % len(styles)]
        code = f"FS-{prefix}-{index:04d}"
        name = f"{category_name.rstrip('s')} {style} {index:03d}"
        price = Decimal(str(base + ((index - 1) % 8) * 10)).quantize(Decimal("0.01"))
        url = f"https://picsum.photos/seed/{code.lower()}/800/1000"

        product = db.scalar(select(Product).where(Product.code == code))
        if product is None:
            product = Product(code=code, name=name, description=f"{name}, colección FashionStore 2026.", brand="FashionStore", base_price=price, cover_image_url=url, category_id=category.id, audience_id=audience.id, is_active=True)
            db.add(product)
            created += 1
        else:
            product.name = name
            product.description = f"{name}, colección FashionStore 2026."
            product.brand = "FashionStore"
            product.base_price = price
            product.cover_image_url = url
            product.category_id = category.id
            product.audience_id = audience.id
            product.is_active = True
            updated += 1
    db.flush()
    print(f"✅ Productos listos: {created} creados, {updated} actualizados.")
