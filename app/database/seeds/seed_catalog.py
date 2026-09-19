from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.seeds.seed_catalog_master import (
    seed_catalog_master,
)
from app.database.seeds.seed_products import (
    seed_products,
)
from app.database.seeds.seed_product_variants import (
    seed_product_variants,
)
from app.database.seeds.seed_product_images import (
    seed_product_images,
)
from app.database.seeds.seed_catalog_relations import (
    seed_catalog_relations,
)
from app.database.seeds.seed_virtual_fitting import (
    seed_virtual_fitting,
)


def seed_catalog(
    db: Session,
) -> None:
    """
    Orquestador completo del Módulo 3.

    Orden:
    1. Datos maestros
    2. 200 productos
    3. 3 variantes talla/color por producto (sin combinatoria cartesiana)
    4. Imágenes
    5. Relaciones de temporada/colección/promoción
    6. Assets del vestidor virtual
    """
    print()
    print("=" * 60)
    print("🛍️  FASHIONSTORE - SEED CATÁLOGO")
    print("=" * 60)

    seed_catalog_master(db)
    seed_products(db)
    seed_product_variants(db)
    seed_product_images(db)
    seed_catalog_relations(db)
    seed_virtual_fitting(db)

    db.commit()

    print("=" * 60)
    print("✅ SEED DE CATÁLOGO COMPLETADO")
    print("=" * 60)
    print()
