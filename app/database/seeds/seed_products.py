from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.audience import Audience
from app.models.product import Product

from app.database.seeds.seed_catalog_utils import (
    first_existing_field,
    safe_bool_payload,
    upsert_model,
)


CATEGORY_CONFIG = {
    "Poleras": {
        "prefix": "POL",
        "count": 35,
        "base_price": 89,
        "audiences": ["Hombre", "Mujer", "Unisex"],
        "names": [
            "Essential",
            "Oversize",
            "Urban",
            "Classic",
            "Street",
            "Minimal",
            "Signature",
        ],
    },
    "Camisas": {
        "prefix": "CAM",
        "count": 25,
        "base_price": 139,
        "audiences": ["Hombre", "Mujer"],
        "names": [
            "Oxford",
            "Smart",
            "Linen",
            "Classic",
            "Urban",
        ],
    },
    "Pantalones": {
        "prefix": "PAN",
        "count": 25,
        "base_price": 169,
        "audiences": ["Hombre", "Mujer", "Unisex"],
        "names": [
            "Cargo",
            "Chino",
            "Relaxed",
            "Formal",
            "Street",
        ],
    },
    "Jeans": {
        "prefix": "JEA",
        "count": 25,
        "base_price": 189,
        "audiences": ["Hombre", "Mujer", "Unisex"],
        "names": [
            "Straight",
            "Slim",
            "Relaxed",
            "Wide",
            "Classic",
        ],
    },
    "Vestidos": {
        "prefix": "VES",
        "count": 30,
        "base_price": 219,
        "audiences": ["Mujer"],
        "names": [
            "Midi",
            "Elegance",
            "Urban",
            "Summer",
            "Night",
            "Classic",
        ],
    },
    "Chaquetas": {
        "prefix": "CHA",
        "count": 20,
        "base_price": 279,
        "audiences": ["Hombre", "Mujer", "Unisex"],
        "names": [
            "Bomber",
            "Urban",
            "Denim",
            "Classic",
            "Street",
        ],
    },
    "Shorts": {
        "prefix": "SHO",
        "count": 20,
        "base_price": 119,
        "audiences": ["Hombre", "Mujer", "Unisex"],
        "names": [
            "Summer",
            "Cargo",
            "Sport",
            "Urban",
            "Basic",
        ],
    },
    "Faldas": {
        "prefix": "FAL",
        "count": 20,
        "base_price": 149,
        "audiences": ["Mujer"],
        "names": [
            "Midi",
            "Urban",
            "Denim",
            "Classic",
            "Pleated",
        ],
    },
}


def _find_by_name(db: Session, model, name: str):
    name_field = first_existing_field(
        model,
        "name",
        "title",
        "label",
    )

    if name_field is None:
        raise RuntimeError(
            f"{model.__name__} no tiene campo name/title/label."
        )

    return db.scalar(
        select(model).where(
            getattr(model, name_field) == name
        )
    )


def seed_products(db: Session) -> None:
    print("🌱 Seed catálogo: 200 productos...")

    global_index = 1

    for category_name, config in CATEGORY_CONFIG.items():
        category = _find_by_name(
            db,
            Category,
            category_name,
        )

        if category is None:
            raise RuntimeError(
                f"No existe categoría '{category_name}'. "
                f"Ejecuta primero seed_catalog_master()."
            )

        for local_index in range(
            1,
            config["count"] + 1,
        ):
            audience_name = config["audiences"][
                (local_index - 1)
                % len(config["audiences"])
            ]

            audience = _find_by_name(
                db,
                Audience,
                audience_name,
            )

            if audience is None:
                raise RuntimeError(
                    f"No existe audiencia '{audience_name}'."
                )

            style_name = config["names"][
                (local_index - 1)
                % len(config["names"])
            ]

            sku = (
                f"FS-{config['prefix']}-"
                f"{local_index:04d}"
            )

            product_name = (
                f"{category_name[:-1] if category_name.endswith('s') else category_name} "
                f"{style_name} {local_index:02d}"
            )

            # Precio determinístico, no aleatorio.
            price = Decimal(
                str(
                    config["base_price"]
                    + ((local_index - 1) % 7) * 10
                )
            )

            cover_url = (
                "https://picsum.photos/seed/"
                f"fashionstore-{sku.lower()}/800/1000"
            )

            payload = {
                "sku": sku,
                "code": sku,
                "name": product_name,
                "title": product_name,
                "description": (
                    f"{product_name}. Prenda de demostración "
                    f"para el catálogo FashionStore."
                ),
                "brand": "FashionStore",
                "price": price,
                "base_price": price,
                "sale_price": price,
                "category_id": getattr(category, "id"),
                "audience_id": getattr(audience, "id"),
                "cover_image_url": cover_url,
                "image_url": cover_url,
                **safe_bool_payload(Product),
            }

            lookup_field = first_existing_field(
                Product,
                "sku",
                "code",
                "name",
                "title",
            )

            if lookup_field is None:
                raise RuntimeError(
                    "Product necesita sku/code/name/title para seed."
                )

            upsert_model(
                db,
                Product,
                payload,
                lookup_field=lookup_field,
            )

            global_index += 1

    db.flush()

    total = global_index - 1

    print(
        f"✅ Productos listos: {total}."
    )
