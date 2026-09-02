from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.size import Size
from app.models.color import Color

from app.database.seeds.seed_catalog_utils import (
    add_relation_if_missing,
    first_existing_field,
    model_columns,
    safe_bool_payload,
    upsert_model,
)


DEFAULT_SIZE_NAMES = [
    "XS",
    "S",
    "M",
    "L",
    "XL",
    "XXL",
]

DEFAULT_COLOR_NAMES = [
    "Negro",
    "Blanco",
    "Azul",
    "Rojo",
    "Verde",
    "Beige",
    "Gris",
    "Marrón",
    "Rosado",
    "Morado",
    "Celeste",
    "Amarillo",
]


def _all_ordered(
    db: Session,
    model,
):
    id_field = first_existing_field(
        model,
        "id",
    )

    stmt = select(model)

    if id_field is not None:
        stmt = stmt.order_by(
            getattr(model, id_field)
        )

    return list(
        db.scalars(stmt).all()
    )


def _display_value(
    obj,
    *candidates,
):
    for candidate in candidates:
        if hasattr(obj, candidate):
            value = getattr(obj, candidate)
            if value is not None:
                return str(value)
    return str(getattr(obj, "id"))


def seed_product_variants(
    db: Session,
) -> None:
    print("🌱 Seed catálogo: variantes producto/talla/color...")

    products = _all_ordered(
        db,
        Product,
    )

    sizes = _all_ordered(
        db,
        Size,
    )

    colors = _all_ordered(
        db,
        Color,
    )

    if not products:
        raise RuntimeError(
            "No hay productos. Ejecuta seed_products primero."
        )

    if not sizes:
        raise RuntimeError(
            "No hay tallas."
        )

    if not colors:
        raise RuntimeError(
            "No hay colores."
        )

    created_or_updated = 0

    for product_index, product in enumerate(
        products,
        start=1,
    ):
        product_code = _display_value(
            product,
            "sku",
            "code",
            "id",
        )

        # 4 tallas + 4 colores = 16 variantes por producto.
        # Desplazamos las selecciones para que no sean idénticas.
        selected_sizes = [
            sizes[
                (product_index + offset)
                % len(sizes)
            ]
            for offset in range(
                min(4, len(sizes))
            )
        ]

        selected_colors = [
            colors[
                (product_index * 2 + offset)
                % len(colors)
            ]
            for offset in range(
                min(4, len(colors))
            )
        ]

        for size in selected_sizes:
            for color in selected_colors:
                size_code = _display_value(
                    size,
                    "code",
                    "name",
                    "label",
                )

                color_code = _display_value(
                    color,
                    "code",
                    "name",
                    "label",
                )

                variant_sku = (
                    f"{product_code}-"
                    f"{size_code}-"
                    f"{color_code}"
                ).upper().replace(
                    " ",
                    "-",
                )

                product_price = (
                    getattr(
                        product,
                        "price",
                        None,
                    )
                    or getattr(
                        product,
                        "base_price",
                        None,
                    )
                    or Decimal("100")
                )

                payload = {
                    "sku": variant_sku,
                    "code": variant_sku,
                    "product_id": getattr(product, "id"),
                    "size_id": getattr(size, "id"),
                    "color_id": getattr(color, "id"),
                    "price": product_price,
                    "additional_price": Decimal("0"),
                    **safe_bool_payload(ProductVariant),
                }

                lookup_field = first_existing_field(
                    ProductVariant,
                    "sku",
                    "code",
                )

                if lookup_field is not None:
                    upsert_model(
                        db,
                        ProductVariant,
                        payload,
                        lookup_field=lookup_field,
                    )
                else:
                    # Si no hay sku/code, usamos la combinación natural.
                    add_relation_if_missing(
                        db,
                        ProductVariant,
                        payload,
                        unique_by=(
                            "product_id",
                            "size_id",
                            "color_id",
                        ),
                    )

                created_or_updated += 1

    db.flush()

    print(
        f"✅ Variantes procesadas: {created_or_updated}."
    )
