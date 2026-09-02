from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_image import ProductImage

from app.database.seeds.seed_catalog_utils import (
    add_relation_if_missing,
    first_existing_field,
    model_columns,
    safe_bool_payload,
)


def _product_key(product) -> str:
    for field in (
        "sku",
        "code",
        "name",
    ):
        if hasattr(product, field):
            value = getattr(
                product,
                field,
            )
            if value:
                return (
                    str(value)
                    .lower()
                    .replace(" ", "-")
                )

    return str(
        getattr(product, "id")
    )


def seed_product_images(
    db: Session,
) -> None:
    print("🌱 Seed catálogo: imágenes de productos...")

    products = list(
        db.scalars(
            select(Product).order_by(
                Product.id
            )
        ).all()
    )

    columns = model_columns(
        ProductImage,
    )

    total = 0

    for product in products:
        key = _product_key(product)

        for index in range(
            1,
            4,
        ):
            image_url = (
                "https://picsum.photos/seed/"
                f"{key}-{index}/800/1000"
            )

            payload = {
                "product_id": getattr(product, "id"),
                "image_url": image_url,
                "url": image_url,
                "alt_text": (
                    f"Imagen {index} del producto {key}"
                ),
                "sort_order": index,
                "position": index,
                "is_primary": index == 1,
                **safe_bool_payload(ProductImage),
            }

            # ProductImage suele no tener sku.
            # La combinación producto + url es idempotente.
            if (
                "product_id" in columns
                and "image_url" in columns
            ):
                add_relation_if_missing(
                    db,
                    ProductImage,
                    payload,
                    unique_by=(
                        "product_id",
                        "image_url",
                    ),
                )
            elif (
                "product_id" in columns
                and "url" in columns
            ):
                add_relation_if_missing(
                    db,
                    ProductImage,
                    payload,
                    unique_by=(
                        "product_id",
                        "url",
                    ),
                )
            else:
                raise RuntimeError(
                    "ProductImage necesita product_id "
                    "y image_url/url."
                )

            total += 1

    db.flush()

    print(
        f"✅ Imágenes procesadas: {total}."
    )
