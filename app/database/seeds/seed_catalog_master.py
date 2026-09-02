from __future__ import annotations

from datetime import date, datetime, timezone
from decimal import Decimal

from sqlalchemy.orm import Session

from app.models.category import Category
from app.models.audience import Audience
from app.models.size import Size
from app.models.color import Color
from app.models.season import Season
from app.models.collection import Collection
from app.models.promotion import Promotion

from app.database.seeds.seed_catalog_utils import (
    safe_bool_payload,
    upsert_model,
)


# =========================================================
# CATEGORÍAS
# =========================================================

CATEGORIES = [
    (
        "Poleras",
        "Poleras y camisetas para diferentes estilos y públicos.",
    ),
    (
        "Camisas",
        "Camisas casuales, formales y urbanas.",
    ),
    (
        "Pantalones",
        "Pantalones casuales, formales y urbanos.",
    ),
    (
        "Jeans",
        "Jeans de diferentes cortes y estilos.",
    ),
    (
        "Vestidos",
        "Vestidos casuales, elegantes y de temporada.",
    ),
    (
        "Chaquetas",
        "Chaquetas urbanas, casuales y de abrigo.",
    ),
    (
        "Shorts",
        "Shorts casuales, deportivos y urbanos.",
    ),
    (
        "Faldas",
        "Faldas de diferentes largos y estilos.",
    ),
]


# =========================================================
# AUDIENCIAS
# =========================================================

AUDIENCES = [
    (
        "Hombre",
        "Prendas orientadas al público masculino.",
    ),
    (
        "Mujer",
        "Prendas orientadas al público femenino.",
    ),
    (
        "Niño",
        "Prendas orientadas a niños.",
    ),
    (
        "Niña",
        "Prendas orientadas a niñas.",
    ),
    (
        "Unisex",
        "Prendas diseñadas para distintos públicos.",
    ),
]


# =========================================================
# TALLAS
# =========================================================

SIZES = [
    (
        "XS",
        "Extra pequeña",
        1,
    ),
    (
        "S",
        "Pequeña",
        2,
    ),
    (
        "M",
        "Mediana",
        3,
    ),
    (
        "L",
        "Grande",
        4,
    ),
    (
        "XL",
        "Extra grande",
        5,
    ),
    (
        "XXL",
        "Doble extra grande",
        6,
    ),
]


# =========================================================
# COLORES
# =========================================================

COLORS = [
    (
        "Negro",
        "#111111",
    ),
    (
        "Blanco",
        "#FFFFFF",
    ),
    (
        "Azul",
        "#1E40AF",
    ),
    (
        "Rojo",
        "#DC2626",
    ),
    (
        "Verde",
        "#15803D",
    ),
    (
        "Beige",
        "#D6C3A5",
    ),
    (
        "Gris",
        "#6B7280",
    ),
    (
        "Marrón",
        "#7C4A2D",
    ),
    (
        "Rosado",
        "#EC4899",
    ),
    (
        "Morado",
        "#7E22CE",
    ),
    (
        "Celeste",
        "#38BDF8",
    ),
    (
        "Amarillo",
        "#FACC15",
    ),
]


# =========================================================
# TEMPORADAS
# =========================================================

SEASONS = [
    (
        "Primavera 2026",
        "Temporada primavera 2026.",
        date(
            2026,
            9,
            21,
        ),
        date(
            2026,
            12,
            20,
        ),
    ),
    (
        "Verano 2026/2027",
        "Temporada verano 2026/2027.",
        date(
            2026,
            12,
            21,
        ),
        date(
            2027,
            3,
            20,
        ),
    ),
    (
        "Otoño 2027",
        "Temporada otoño 2027.",
        date(
            2027,
            3,
            21,
        ),
        date(
            2027,
            6,
            20,
        ),
    ),
    (
        "Invierno 2027",
        "Temporada invierno 2027.",
        date(
            2027,
            6,
            21,
        ),
        date(
            2027,
            9,
            20,
        ),
    ),
]


# =========================================================
# COLECCIONES
# =========================================================

COLLECTIONS = [
    (
        "Urban Essentials",
        "Prendas esenciales de estilo urbano.",
        date(
            2026,
            8,
            1,
        ),
    ),
    (
        "Denim Core",
        "Colección centrada en prendas denim.",
        date(
            2026,
            8,
            5,
        ),
    ),
    (
        "Night Edit",
        "Colección para estilos nocturnos y elegantes.",
        date(
            2026,
            8,
            10,
        ),
    ),
    (
        "Basic Line",
        "Básicos versátiles para uso diario.",
        date(
            2026,
            8,
            15,
        ),
    ),
    (
        "Active Street",
        "Estilo urbano con inspiración deportiva.",
        date(
            2026,
            8,
            20,
        ),
    ),
    (
        "Kids Color",
        "Colección colorida para niños y niñas.",
        date(
            2026,
            8,
            22,
        ),
    ),
    (
        "Smart Casual",
        "Prendas casuales con acabado más formal.",
        date(
            2026,
            8,
            25,
        ),
    ),
    (
        "Summer Move",
        "Prendas ligeras para clima cálido.",
        date(
            2026,
            8,
            28,
        ),
    ),
]


# =========================================================
# PROMOCIONES
# =========================================================
#
# IMPORTANTE:
# El modelo Promotion REAL utiliza:
#
# - name
# - description
# - discount_type
# - discount_value
# - start_at
# - end_at
# - is_active
#
# NO utiliza:
# - code
# - discount_percentage
# - start_date
# - end_date
#
# Por eso estos datos ya están adaptados exactamente al modelo.
# =========================================================

PROMOTIONS = [
    (
        "Bienvenida 10%",
        "Promoción de bienvenida con 10% de descuento.",
        "PERCENTAGE",
        Decimal(
            "10.00",
        ),
        datetime(
            2026,
            8,
            1,
            0,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        datetime(
            2027,
            12,
            31,
            23,
            59,
            59,
            tzinfo=timezone.utc,
        ),
    ),
    (
        "Mid Season 15%",
        "Promoción de media temporada con 15% de descuento.",
        "PERCENTAGE",
        Decimal(
            "15.00",
        ),
        datetime(
            2026,
            8,
            1,
            0,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        datetime(
            2027,
            12,
            31,
            23,
            59,
            59,
            tzinfo=timezone.utc,
        ),
    ),
    (
        "Fashion 20%",
        "Promoción FashionStore con 20% de descuento.",
        "PERCENTAGE",
        Decimal(
            "20.00",
        ),
        datetime(
            2026,
            8,
            1,
            0,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        datetime(
            2027,
            12,
            31,
            23,
            59,
            59,
            tzinfo=timezone.utc,
        ),
    ),
    (
        "VIP 25%",
        "Promoción VIP con 25% de descuento.",
        "PERCENTAGE",
        Decimal(
            "25.00",
        ),
        datetime(
            2026,
            8,
            1,
            0,
            0,
            0,
            tzinfo=timezone.utc,
        ),
        datetime(
            2027,
            12,
            31,
            23,
            59,
            59,
            tzinfo=timezone.utc,
        ),
    ),
]


# =========================================================
# SEED
# =========================================================

def seed_catalog_master(
    db: Session,
) -> None:

    print(
        "🌱 Seed catálogo: datos maestros..."
    )


    # =====================================================
    # CATEGORÍAS
    # =====================================================

    for (
        name,
        description,
    ) in CATEGORIES:

        upsert_model(
            db,
            Category,
            {
                "name":
                    name,

                "description":
                    description,

                **safe_bool_payload(
                    Category,
                ),
            },
            lookup_field=
                "name",
        )


    # =====================================================
    # AUDIENCIAS
    # =====================================================

    for (
        name,
        description,
    ) in AUDIENCES:

        upsert_model(
            db,
            Audience,
            {
                "name":
                    name,

                "description":
                    description,

                **safe_bool_payload(
                    Audience,
                ),
            },
            lookup_field=
                "name",
        )


    # =====================================================
    # TALLAS
    # =====================================================

    for (
        name,
        description,
        sort_order,
    ) in SIZES:

        upsert_model(
            db,
            Size,
            {
                "name":
                    name,

                "description":
                    description,

                "sort_order":
                    sort_order,

                **safe_bool_payload(
                    Size,
                ),
            },
            lookup_field=
                "name",
        )


    # =====================================================
    # COLORES
    # =====================================================

    for (
        name,
        hex_code,
    ) in COLORS:

        upsert_model(
            db,
            Color,
            {
                "name":
                    name,

                "hex_code":
                    hex_code,

                **safe_bool_payload(
                    Color,
                ),
            },
            lookup_field=
                "name",
        )


    # =====================================================
    # TEMPORADAS
    # =====================================================

    for (
        name,
        description,
        start_date,
        end_date,
    ) in SEASONS:

        upsert_model(
            db,
            Season,
            {
                "name":
                    name,

                "description":
                    description,

                "start_date":
                    start_date,

                "end_date":
                    end_date,

                **safe_bool_payload(
                    Season,
                ),
            },
            lookup_field=
                "name",
        )


    # =====================================================
    # COLECCIONES
    # =====================================================

    for (
        name,
        description,
        launch_date,
    ) in COLLECTIONS:

        upsert_model(
            db,
            Collection,
            {
                "name":
                    name,

                "description":
                    description,

                "launch_date":
                    launch_date,

                **safe_bool_payload(
                    Collection,
                ),
            },
            lookup_field=
                "name",
        )


    # =====================================================
    # PROMOCIONES
    # =====================================================

    for (
        name,
        description,
        discount_type,
        discount_value,
        start_at,
        end_at,
    ) in PROMOTIONS:

        upsert_model(
            db,
            Promotion,
            {
                "name":
                    name,

                "description":
                    description,

                "discount_type":
                    discount_type,

                "discount_value":
                    discount_value,

                "start_at":
                    start_at,

                "end_at":
                    end_at,

                **safe_bool_payload(
                    Promotion,
                ),
            },
            lookup_field=
                "name",
        )


    db.flush()


    print(
        "✅ Datos maestros del catálogo listos."
    )
