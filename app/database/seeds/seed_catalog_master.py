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
from app.database.seeds.seed_catalog_utils import safe_bool_payload, upsert_model

CATEGORIES = [
    ("Poleras", "Poleras y camisetas para diferentes estilos y públicos."),
    ("Camisas", "Camisas casuales, formales y urbanas."),
    ("Pantalones", "Pantalones casuales, formales y urbanos."),
    ("Jeans", "Jeans de diferentes cortes y estilos."),
    ("Vestidos", "Vestidos casuales, elegantes y de temporada."),
    ("Chaquetas", "Chaquetas urbanas, casuales y de abrigo."),
    ("Shorts", "Shorts casuales, deportivos y urbanos."),
    ("Faldas", "Faldas de diferentes largos y estilos."),
]

AUDIENCES = [
    ("Hombre", "Prendas orientadas al público masculino."),
    ("Mujer", "Prendas orientadas al público femenino."),
    ("Niño", "Prendas orientadas a niños."),
    ("Niña", "Prendas orientadas a niñas."),
    ("Unisex", "Prendas diseñadas para distintos públicos."),
]

SIZES = [
    ("XS", "Extra pequeña", 1), ("S", "Pequeña", 2),
    ("M", "Mediana", 3), ("L", "Grande", 4),
    ("XL", "Extra grande", 5), ("XXL", "Doble extra grande", 6),
]

COLORS = [
    ("Negro", "#111111"), ("Blanco", "#FFFFFF"), ("Azul", "#1E40AF"),
    ("Rojo", "#DC2626"), ("Verde", "#15803D"), ("Beige", "#D6C3A5"),
    ("Gris", "#6B7280"), ("Marrón", "#7C4A2D"), ("Rosado", "#EC4899"),
    ("Morado", "#7E22CE"), ("Celeste", "#38BDF8"), ("Amarillo", "#FACC15"),
]

# (name, description, start_date, end_date, is_active)
SEASONS = [
    ("Verano 2025/2026", "Temporada verano 2025/2026.", date(2025, 12, 21), date(2026, 3, 20), False),
    ("Otoño 2026", "Temporada otoño 2026.", date(2026, 3, 21), date(2026, 6, 20), False),
    ("Invierno 2026", "Temporada invierno 2026.", date(2026, 6, 21), date(2026, 9, 20), True),
    ("Primavera 2026", "Temporada primavera 2026.", date(2026, 9, 21), date(2026, 12, 20), True),
    ("Verano 2026/2027", "Temporada verano 2026/2027.", date(2026, 12, 21), date(2027, 3, 20), True),
]

# (name, description, launch_date, is_active)
COLLECTIONS = [
    ("Urban Essentials", "Prendas esenciales de estilo urbano.", date(2026, 1, 20), True),
    ("Denim Core", "Colección centrada en prendas denim.", date(2026, 3, 10), True),
    ("Night Edit", "Colección para estilos nocturnos y elegantes.", date(2026, 5, 5), True),
    ("Basic Line", "Básicos versátiles para uso diario.", date(2026, 6, 15), True),
    ("Active Street", "Estilo urbano con inspiración deportiva.", date(2026, 7, 20), True),
    ("Kids Color", "Colección colorida para niños y niñas.", date(2026, 8, 5), True),
    ("Smart Casual", "Prendas casuales con acabado más formal.", date(2026, 8, 25), True),
    ("Summer Move", "Prendas ligeras para clima cálido.", date(2026, 12, 1), False),
]

# Exactamente una promoción activa al 18/09/2026.
# (name, description, type, value, start_at, end_at, is_active)
PROMOTIONS = [
    ("Verano 10%", "Promoción histórica de verano.", "PERCENTAGE", Decimal("10.00"), datetime(2026, 1, 10, tzinfo=timezone.utc), datetime(2026, 2, 28, 23, 59, 59, tzinfo=timezone.utc), False),
    ("Mid Season 15%", "Promoción histórica de media temporada.", "PERCENTAGE", Decimal("15.00"), datetime(2026, 4, 1, tzinfo=timezone.utc), datetime(2026, 4, 30, 23, 59, 59, tzinfo=timezone.utc), False),
    ("Invierno 12%", "Promoción histórica de invierno.", "PERCENTAGE", Decimal("12.00"), datetime(2026, 7, 1, tzinfo=timezone.utc), datetime(2026, 7, 31, 23, 59, 59, tzinfo=timezone.utc), False),
    ("Septiembre Fashion 20%", "20% de descuento en prendas seleccionadas durante septiembre.", "PERCENTAGE", Decimal("20.00"), datetime(2026, 9, 1, tzinfo=timezone.utc), datetime(2026, 10, 15, 23, 59, 59, tzinfo=timezone.utc), True),
]

def seed_catalog_master(db: Session) -> None:
    print("🌱 Seed catálogo: datos maestros...")

    for name, description in CATEGORIES:
        upsert_model(db, Category, {"name": name, "description": description, **safe_bool_payload(Category)}, lookup_field="name")

    for name, description in AUDIENCES:
        upsert_model(db, Audience, {"name": name, "description": description, **safe_bool_payload(Audience)}, lookup_field="name")

    for name, description, sort_order in SIZES:
        upsert_model(db, Size, {"name": name, "description": description, "sort_order": sort_order, **safe_bool_payload(Size)}, lookup_field="name")

    for name, hex_code in COLORS:
        upsert_model(db, Color, {"name": name, "hex_code": hex_code, **safe_bool_payload(Color)}, lookup_field="name")

    for name, description, start_date, end_date, active in SEASONS:
        upsert_model(db, Season, {"name": name, "description": description, "start_date": start_date, "end_date": end_date, **safe_bool_payload(Season, active=active)}, lookup_field="name")

    for name, description, launch_date, active in COLLECTIONS:
        upsert_model(db, Collection, {"name": name, "description": description, "launch_date": launch_date, **safe_bool_payload(Collection, active=active)}, lookup_field="name")

    for name, description, discount_type, discount_value, start_at, end_at, active in PROMOTIONS:
        upsert_model(db, Promotion, {
            "name": name, "description": description, "discount_type": discount_type,
            "discount_value": discount_value, "start_at": start_at, "end_at": end_at,
            **safe_bool_payload(Promotion, active=active),
        }, lookup_field="name")

    db.flush()
    print("✅ Datos maestros del catálogo listos.")
