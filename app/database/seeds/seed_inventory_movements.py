from __future__ import annotations

from collections import defaultdict
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.employee_branch import EmployeeBranch
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.product_variant import ProductVariant
from app.models.supplier_availability import SupplierAvailability
from app.models.supplier_product import SupplierProduct


SEED_REFERENCE_PREFIX = "SEED-INV"


def _money(
    value,
) -> Decimal | None:

    if value is None:
        return None

    return Decimal(
        str(value)
    ).quantize(
        Decimal("0.01")
    )


def _create_movement(
    db: Session,
    *,
    inventory: Inventory,
    movement_type: str,
    quantity: int,
    stock_before: int,
    stock_after: int,
    reserved_before: int,
    reserved_after: int,
    user_id: int | None,
    reference_code: str,
    reason: str,
    supplier_id: int | None = None,
    unit_cost: Decimal | None = None,
    notes: str | None = None,
) -> InventoryMovement:

    movement = InventoryMovement(
        inventory_id=inventory.id,
        movement_type=movement_type,
        quantity=quantity,
        stock_before=stock_before,
        stock_after=stock_after,
        reserved_before=reserved_before,
        reserved_after=reserved_after,
        supplier_id=supplier_id,
        user_id=user_id,
        unit_cost=unit_cost,
        reference_type="SEED_INVENTORY",
        reference_id=None,
        reference_code=reference_code,
        reason=reason,
        notes=notes,
    )

    db.add(
        movement
    )

    return movement


def seed_inventory_movements(
    db: Session,
) -> None:

    print(
        "🌱 Seed inventario: movimientos y stock inicial..."
    )

    inventories = list(
        db.scalars(
            select(Inventory)
            .where(
                Inventory.is_active.is_(True)
            )
            .order_by(
                Inventory.id
            )
        ).all()
    )

    if not inventories:
        raise RuntimeError(
            "No hay inventarios. "
            "Ejecuta seed_inventories primero."
        )

    # =====================================================
    # EMPLEADO ACTIVO POR SUCURSAL
    # =====================================================
    #
    # seed_locations ya asigna empleados a sucursales.
    # Para los movimientos seed usamos un empleado activo
    # de la misma sucursal como usuario responsable.
    # =====================================================

    branch_user_map: dict[int, int] = {}

    assignments = list(
        db.scalars(
            select(EmployeeBranch)
            .where(
                EmployeeBranch.is_active.is_(True)
            )
            .order_by(
                EmployeeBranch.id
            )
        ).all()
    )

    for assignment in assignments:
        branch_user_map.setdefault(
            assignment.branch_id,
            assignment.user_id,
        )

    # =====================================================
    # PRODUCTO DE CADA VARIANTE
    # =====================================================

    variants = list(
        db.scalars(
            select(ProductVariant)
            .order_by(
                ProductVariant.id
            )
        ).all()
    )

    variant_product_map = {
        variant.id:
            variant.product_id
        for variant in variants
    }

    # =====================================================
    # DISPONIBILIDAD DE PROVEEDORES POR VARIANTE
    # =====================================================
    #
    # El módulo 4 ya genera:
    #
    # Supplier
    #   -> SupplierProduct
    #       -> SupplierAvailability
    #
    # Para la entrada inicial elegimos un proveedor que
    # realmente tenga registrada esa variante.
    # =====================================================

    provider_options: dict[
        int,
        list[
            tuple[
                SupplierAvailability,
                SupplierProduct,
            ]
        ],
    ] = defaultdict(
        list
    )

    rows = db.execute(
        select(
            SupplierAvailability,
            SupplierProduct,
        )
        .join(
            SupplierProduct,
            SupplierProduct.id
            == SupplierAvailability.supplier_product_id,
        )
        .where(
            SupplierAvailability.available_quantity > 0
        )
        .order_by(
            SupplierAvailability.product_variant_id,
            SupplierAvailability.id,
        )
    ).all()

    for availability, supplier_product in rows:

        provider_options[
            availability.product_variant_id
        ].append(
            (
                availability,
                supplier_product,
            )
        )

    # Fallback por producto.
    # Normalmente no se usa porque el seed de proveedores
    # genera disponibilidad para todas las variantes.
    supplier_products_by_product: dict[
        int,
        list[SupplierProduct],
    ] = defaultdict(
        list
    )

    supplier_products = list(
        db.scalars(
            select(SupplierProduct)
            .where(
                SupplierProduct.is_active.is_(True)
            )
            .order_by(
                SupplierProduct.id
            )
        ).all()
    )

    for supplier_product in supplier_products:
        supplier_products_by_product[
            supplier_product.product_id
        ].append(
            supplier_product
        )

    # =====================================================
    # CÓDIGOS DE MOVIMIENTO YA CREADOS
    # =====================================================
    #
    # Esto hace el seed idempotente.
    # Si un inventario ya tiene su movimiento ENTRY seed,
    # no volvemos a tocar su stock ni a duplicar historial.
    # =====================================================

    existing_seed_codes = set(
        db.scalars(
            select(
                InventoryMovement.reference_code
            )
            .where(
                InventoryMovement.reference_code.like(
                    f"{SEED_REFERENCE_PREFIX}-%"
                )
            )
        ).all()
    )

    movements_created = 0
    inventories_seeded = 0
    inventories_skipped = 0

    for inventory in inventories:

        entry_code = (
            f"{SEED_REFERENCE_PREFIX}-"
            f"{inventory.id:06d}-ENTRY"
        )

        if entry_code in existing_seed_codes:
            inventories_skipped += 1
            continue

        user_id = branch_user_map.get(
            inventory.branch_id
        )

        options = provider_options.get(
            inventory.product_variant_id,
            [],
        )

        supplier_id: int | None = None
        unit_cost: Decimal | None = None
        supplier_available_quantity: int | None = None

        if options:

            option_index = (
                inventory.branch_id
                + inventory.product_variant_id
            ) % len(options)

            (
                availability,
                supplier_product,
            ) = options[
                option_index
            ]

            supplier_id = (
                supplier_product.supplier_id
            )

            unit_cost = _money(
                availability.purchase_price
                if availability.purchase_price is not None
                else supplier_product.purchase_price
            )

            supplier_available_quantity = (
                availability.available_quantity
            )

        else:

            product_id = (
                variant_product_map.get(
                    inventory.product_variant_id
                )
            )

            fallback_options = (
                supplier_products_by_product.get(
                    product_id,
                    [],
                )
            )

            if fallback_options:

                supplier_product = fallback_options[
                    (
                        inventory.branch_id
                        + inventory.product_variant_id
                    )
                    % len(fallback_options)
                ]

                supplier_id = (
                    supplier_product.supplier_id
                )

                unit_cost = _money(
                    supplier_product.purchase_price
                )

        # =================================================
        # ENTRADA INICIAL
        # =================================================

        desired_quantity = (
            12
            + (
                (
                    inventory.id * 7
                    + inventory.branch_id * 3
                )
                % 39
            )
        )

        if (
            supplier_available_quantity is not None
            and supplier_available_quantity > 0
        ):
            entry_quantity = min(
                desired_quantity,
                supplier_available_quantity,
            )
        else:
            entry_quantity = desired_quantity

        entry_quantity = max(
            1,
            entry_quantity,
        )

        _create_movement(
            db,
            inventory=inventory,
            movement_type="ENTRY",
            quantity=entry_quantity,
            stock_before=0,
            stock_after=entry_quantity,
            reserved_before=0,
            reserved_after=0,
            supplier_id=supplier_id,
            user_id=user_id,
            unit_cost=unit_cost,
            reference_code=entry_code,
            reason="Carga inicial de inventario desde proveedor.",
            notes=(
                "Movimiento generado por el seed del "
                "Módulo 5 - Inventario."
            ),
        )

        inventory.stock_quantity = (
            entry_quantity
        )

        inventory.reserved_quantity = 0

        existing_seed_codes.add(
            entry_code
        )

        movements_created += 1

        # =================================================
        # ALGUNAS VARIANTES QUEDAN AGOTADAS
        # =================================================
        #
        # Esto permite probar consultas de stock 0.
        # Se registra como movimiento, no cambiando stock
        # directamente.
        # =================================================

        if inventory.id % 19 == 0:

            adjustment_code = (
                f"{SEED_REFERENCE_PREFIX}-"
                f"{inventory.id:06d}-OUT"
            )

            stock_before = (
                inventory.stock_quantity
            )

            _create_movement(
                db,
                inventory=inventory,
                movement_type="ADJUSTMENT_OUT",
                quantity=stock_before,
                stock_before=stock_before,
                stock_after=0,
                reserved_before=0,
                reserved_after=0,
                supplier_id=None,
                user_id=user_id,
                unit_cost=None,
                reference_code=adjustment_code,
                reason=(
                    "Ajuste de demostración: "
                    "variante agotada en sucursal."
                ),
            )

            inventory.stock_quantity = 0

            existing_seed_codes.add(
                adjustment_code
            )

            movements_created += 1

        else:

            # =============================================
            # AJUSTE NEGATIVO PEQUEÑO
            # =============================================

            if (
                inventory.id % 11 == 0
                and inventory.stock_quantity > 1
            ):

                adjustment_code = (
                    f"{SEED_REFERENCE_PREFIX}-"
                    f"{inventory.id:06d}-ADJOUT"
                )

                stock_before = (
                    inventory.stock_quantity
                )

                quantity = 1

                stock_after = (
                    stock_before
                    - quantity
                )

                _create_movement(
                    db,
                    inventory=inventory,
                    movement_type="ADJUSTMENT_OUT",
                    quantity=quantity,
                    stock_before=stock_before,
                    stock_after=stock_after,
                    reserved_before=0,
                    reserved_after=0,
                    supplier_id=None,
                    user_id=user_id,
                    unit_cost=None,
                    reference_code=adjustment_code,
                    reason=(
                        "Ajuste de inventario por conteo físico."
                    ),
                )

                inventory.stock_quantity = (
                    stock_after
                )

                existing_seed_codes.add(
                    adjustment_code
                )

                movements_created += 1

            # =============================================
            # AJUSTE POSITIVO PEQUEÑO
            # =============================================

            if inventory.id % 17 == 0:

                adjustment_code = (
                    f"{SEED_REFERENCE_PREFIX}-"
                    f"{inventory.id:06d}-ADJIN"
                )

                stock_before = (
                    inventory.stock_quantity
                )

                quantity = 2

                stock_after = (
                    stock_before
                    + quantity
                )

                _create_movement(
                    db,
                    inventory=inventory,
                    movement_type="ADJUSTMENT_IN",
                    quantity=quantity,
                    stock_before=stock_before,
                    stock_after=stock_after,
                    reserved_before=0,
                    reserved_after=0,
                    supplier_id=None,
                    user_id=user_id,
                    unit_cost=None,
                    reference_code=adjustment_code,
                    reason=(
                        "Ajuste de inventario por regularización."
                    ),
                )

                inventory.stock_quantity = (
                    stock_after
                )

                existing_seed_codes.add(
                    adjustment_code
                )

                movements_created += 1

        inventories_seeded += 1

    db.flush()

    print(
        "✅ Stock y movimientos listos: "
        f"{inventories_seeded} inventarios inicializados, "
        f"{inventories_skipped} omitidos por existir, "
        f"{movements_created} movimientos creados."
    )
