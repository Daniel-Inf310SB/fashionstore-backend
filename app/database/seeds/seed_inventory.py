from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.seeds.seed_inventories import (
    seed_inventories,
)
from app.database.seeds.seed_inventory_movements import (
    seed_inventory_movements,
)


def seed_inventory(
    db: Session,
) -> None:

    print()
    print(
        "=" * 60
    )
    print(
        "📦 FASHIONSTORE - SEED INVENTARIO"
    )
    print(
        "=" * 60
    )

    # =====================================================
    # 1. CREAR INVENTARIOS
    # =====================================================
    #
    # Crea las combinaciones:
    #
    # Branch + ProductVariant
    #
    # con stock inicial 0.
    # =====================================================

    seed_inventories(
        db
    )

    # =====================================================
    # 2. CREAR MOVIMIENTOS
    # =====================================================
    #
    # Registra la entrada inicial desde proveedor y actualiza
    # stock_quantity mediante movimientos auditables.
    # =====================================================

    seed_inventory_movements(
        db
    )

    db.commit()

    print(
        "=" * 60
    )
    print(
        "✅ SEED DE INVENTARIO COMPLETADO"
    )
    print(
        "=" * 60
    )
    print()
