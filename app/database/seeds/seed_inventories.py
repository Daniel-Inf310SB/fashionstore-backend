from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.inventory import Inventory
from app.models.product_variant import ProductVariant


# =========================================================
# CONFIGURACIÓN DEL SEED
# =========================================================
#
# El catálogo actual genera aproximadamente:
#   120 productos x 3 variantes = 360 ProductVariant
#
# Existen 27 sucursales.
#
# Crear TODAS las combinaciones daría unas 86.400 filas de inventario,
# demasiado para un MVP local. Para tener datos realistas sin inflar
# innecesariamente la BD, cada variante se distribuye de forma
# determinística en 4 sucursales.
#
# Con 360 variantes:
#   ~1.440 filas Inventory
#
# Esto permite:
#   - stock distinto por sucursal
#   - variantes que no existen en algunas sucursales
#   - consulta global real agregando varias sucursales
# =========================================================

BRANCHES_PER_VARIANT = 4


def _target_branch_indexes(
    variant_id: int,
    branch_count: int,
) -> list[int]:
    """
    Selecciona sucursales de forma determinística.

    No usa random, por lo que ejecutar nuevamente el seed
    mantiene exactamente la misma distribución.
    """
    if branch_count <= 0:
        return []

    wanted = min(
        BRANCHES_PER_VARIANT,
        branch_count,
    )

    indexes: list[int] = []
    step = 11

    offset = 0

    while len(indexes) < wanted:
        index = (
            variant_id * 7
            + offset * step
        ) % branch_count

        if index not in indexes:
            indexes.append(index)

        offset += 1

    return indexes


def seed_inventories(
    db: Session,
) -> None:

    print(
        "🌱 Seed inventario: existencias por sucursal..."
    )

    branches = list(
        db.scalars(
            select(Branch)
            .where(
                Branch.is_active.is_(True)
            )
            .order_by(
                Branch.id
            )
        ).all()
    )

    variants = list(
        db.scalars(
            select(ProductVariant)
            .where(
                ProductVariant.is_active.is_(True)
            )
            .order_by(
                ProductVariant.id
            )
        ).all()
    )

    if not branches:
        raise RuntimeError(
            "No hay sucursales activas. "
            "Ejecuta seed_locations antes del inventario."
        )

    if not variants:
        raise RuntimeError(
            "No hay variantes de producto activas. "
            "Ejecuta seed_catalog antes del inventario."
        )

    # =====================================================
    # CARGAR INVENTARIOS EXISTENTES UNA SOLA VEZ
    # =====================================================

    existing_pairs = set(
        db.execute(
            select(
                Inventory.branch_id,
                Inventory.product_variant_id,
            )
        ).all()
    )

    created = 0
    existing = 0

    for variant in variants:

        branch_indexes = _target_branch_indexes(
            variant.id,
            len(branches),
        )

        for branch_index in branch_indexes:

            branch = branches[
                branch_index
            ]

            key = (
                branch.id,
                variant.id,
            )

            if key in existing_pairs:
                existing += 1
                continue

            # =============================================
            # CONFIGURACIÓN DE CONTROL DE STOCK
            # =============================================
            #
            # El stock físico empieza en 0.
            #
            # IMPORTANTE:
            # seed_inventory_movements.py será quien registre
            # la entrada inicial desde proveedor y actualice
            # stock_quantity. Así el stock siempre tendrá
            # trazabilidad desde el primer momento.
            # =============================================

            minimum_stock = (
                3
                + (
                    (
                        branch.id
                        + variant.id
                    )
                    % 5
                )
            )

            reorder_point = (
                minimum_stock
                + 2
            )

            maximum_stock = (
                40
                + (
                    (
                        branch.id * 3
                        + variant.id
                    )
                    % 5
                )
                * 10
            )

            inventory = Inventory(
                branch_id=branch.id,
                product_variant_id=variant.id,
                stock_quantity=0,
                reserved_quantity=0,
                minimum_stock=minimum_stock,
                maximum_stock=maximum_stock,
                reorder_point=reorder_point,
                is_active=True,
            )

            db.add(
                inventory
            )

            existing_pairs.add(
                key
            )

            created += 1

    db.flush()

    print(
        "✅ Inventarios listos: "
        f"{created} creados, "
        f"{existing} ya existentes."
    )
