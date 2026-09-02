from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.category import Category
from app.models.color import Color
from app.models.virtual_fitting_asset import VirtualFittingAsset

from app.database.seeds.seed_catalog_utils import (
    add_relation_if_missing,
    first_existing_field,
    model_columns,
    safe_bool_payload,
)


FITTING_CATEGORY_TO_TYPE = {
    "Poleras": "TOP",
    "Camisas": "TOP",
    "Chaquetas": "JACKET",
    "Vestidos": "DRESS",
    "Pantalones": "BOTTOM",
    "Jeans": "BOTTOM",
    "Shorts": "BOTTOM",
    "Faldas": "BOTTOM",
}


def _name(obj) -> str:
    for field in (
        "name",
        "title",
        "label",
    ):
        if hasattr(obj, field):
            value = getattr(
                obj,
                field,
            )
            if value:
                return str(value)

    return str(
        getattr(obj, "id")
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


def seed_virtual_fitting(
    db: Session,
) -> None:
    print("🌱 Seed catálogo: assets de vestidor virtual...")

    products = list(
        db.scalars(
            select(Product).order_by(
                Product.id
            )
        ).all()
    )

    colors = list(
        db.scalars(
            select(Color).order_by(
                Color.id
            )
        ).all()
    )

    categories = {
        getattr(category, "id"):
            _name(category)
        for category in db.scalars(
            select(Category)
        ).all()
    }

    columns = model_columns(
        VirtualFittingAsset,
    )

    total = 0

    for index, product in enumerate(
        products,
        start=1,
    ):
        category_id = getattr(
            product,
            "category_id",
            None,
        )

        category_name = categories.get(
            category_id,
            "",
        )

        garment_type = (
            FITTING_CATEGORY_TO_TYPE
            .get(
                category_name,
                "TOP",
            )
        )

        # Para el MVP damos asset a todos los productos.
        # Si quieres limitarlo luego, filtramos categorías.
        color = (
            colors[
                index % len(colors)
            ]
            if colors
            else None
        )

        key = _product_key(
            product,
        )

        png_url = (
            f"/assets/fitting/2d/{key}.png"
        )

        payload = {
            "product_id": getattr(product, "id"),
            "color_id": (
                getattr(color, "id")
                if color is not None
                else None
            ),
            "asset_url": png_url,
            "url": png_url,
            "asset_type": "PNG_OVERLAY",
            "garment_type": garment_type,
            **safe_bool_payload(VirtualFittingAsset),
        }

        if (
            "product_id" in columns
            and "asset_url" in columns
        ):
            add_relation_if_missing(
                db,
                VirtualFittingAsset,
                payload,
                unique_by=(
                    "product_id",
                    "asset_url",
                ),
            )
        elif (
            "product_id" in columns
            and "url" in columns
        ):
            add_relation_if_missing(
                db,
                VirtualFittingAsset,
                payload,
                unique_by=(
                    "product_id",
                    "url",
                ),
            )
        else:
            raise RuntimeError(
                "VirtualFittingAsset necesita product_id "
                "y asset_url/url."
            )

        total += 1

        # Dejamos preparado un asset 3D para 1 de cada 10 productos.
        # Esto te permitirá probar después GLB/Unity sin cambiar DB.
        if index % 10 == 0:
            glb_url = (
                f"/assets/fitting/3d/{key}.glb"
            )

            payload_3d = {
                "product_id": getattr(product, "id"),
                "color_id": (
                    getattr(color, "id")
                    if color is not None
                    else None
                ),
                "asset_url": glb_url,
                "url": glb_url,
                "asset_type": "MODEL_3D",
                "garment_type": garment_type,
                **safe_bool_payload(
                    VirtualFittingAsset,
                ),
            }

            if "asset_url" in columns:
                add_relation_if_missing(
                    db,
                    VirtualFittingAsset,
                    payload_3d,
                    unique_by=(
                        "product_id",
                        "asset_url",
                    ),
                )
            elif "url" in columns:
                add_relation_if_missing(
                    db,
                    VirtualFittingAsset,
                    payload_3d,
                    unique_by=(
                        "product_id",
                        "url",
                    ),
                )

            total += 1

    db.flush()

    print(
        f"✅ Assets de vestidor procesados: {total}."
    )
