from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.season import Season
from app.models.collection import Collection
from app.models.promotion import Promotion
from app.models.product_season import ProductSeason
from app.models.product_collection import ProductCollection
from app.models.product_promotion import ProductPromotion

from app.database.seeds.seed_catalog_utils import (
    add_relation_if_missing,
)


def seed_catalog_relations(
    db: Session,
) -> None:
    print("🌱 Seed catálogo: temporadas, colecciones y promociones...")

    products = list(
        db.scalars(
            select(Product).order_by(
                Product.id
            )
        ).all()
    )

    seasons = list(
        db.scalars(
            select(Season).order_by(
                Season.id
            )
        ).all()
    )

    collections = list(
        db.scalars(
            select(Collection).order_by(
                Collection.id
            )
        ).all()
    )

    promotions = list(
        db.scalars(
            select(Promotion).order_by(
                Promotion.id
            )
        ).all()
    )

    if not products:
        raise RuntimeError(
            "No hay productos."
        )

    if not seasons:
        raise RuntimeError(
            "No hay temporadas."
        )

    if not collections:
        raise RuntimeError(
            "No hay colecciones."
        )

    if not promotions:
        raise RuntimeError(
            "No hay promociones."
        )

    season_total = 0
    collection_total = 0
    promotion_total = 0

    for index, product in enumerate(
        products,
        start=1,
    ):
        season = seasons[
            index % len(seasons)
        ]

        collection = collections[
            (index * 2)
            % len(collections)
        ]

        add_relation_if_missing(
            db,
            ProductSeason,
            {
                "product_id": getattr(product, "id"),
                "season_id": getattr(season, "id"),
            },
            unique_by=(
                "product_id",
                "season_id",
            ),
        )

        season_total += 1

        add_relation_if_missing(
            db,
            ProductCollection,
            {
                "product_id": getattr(product, "id"),
                "collection_id": getattr(
                    collection,
                    "id",
                ),
            },
            unique_by=(
                "product_id",
                "collection_id",
            ),
        )

        collection_total += 1

        # No todos los productos tienen promoción.
        # Aproximadamente uno de cada 4.
        if index % 4 == 0:
            promotion = promotions[
                index % len(promotions)
            ]

            add_relation_if_missing(
                db,
                ProductPromotion,
                {
                    "product_id": getattr(product, "id"),
                    "promotion_id": getattr(
                        promotion,
                        "id",
                    ),
                },
                unique_by=(
                    "product_id",
                    "promotion_id",
                ),
            )

            promotion_total += 1

    db.flush()

    print(
        "✅ Relaciones listas: "
        f"{season_total} temporadas, "
        f"{collection_total} colecciones, "
        f"{promotion_total} promociones."
    )
