from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.seeds.seed_suppliers import (
    seed_suppliers,
)
from app.database.seeds.seed_supplier_products import (
    seed_supplier_products,
)
from app.database.seeds.seed_supplier_availability import (
    seed_supplier_availability,
)


def seed_providers(
    db: Session,
) -> None:

    print()
    print(
        "=" * 60
    )
    print(
        "🚚 FASHIONSTORE - SEED PROVEEDORES"
    )
    print(
        "=" * 60
    )

    seed_suppliers(
        db
    )

    seed_supplier_products(
        db
    )

    seed_supplier_availability(
        db
    )

    db.commit()

    print(
        "=" * 60
    )
    print(
        "✅ SEED DE PROVEEDORES COMPLETADO"
    )
    print(
        "=" * 60
    )
    print()
