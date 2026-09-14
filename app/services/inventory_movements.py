from __future__ import annotations

import math

from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import (
    or_,
)

from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.branch import Branch

from app.models.inventory import Inventory

from app.models.inventory_movement import (
    InventoryMovement,
)

from app.models.product import Product

from app.models.product_variant import (
    ProductVariant,
)

from app.models.supplier import Supplier

from app.models.supplier_availability import (
    SupplierAvailability,
)

from app.models.supplier_product import (
    SupplierProduct,
)

from app.schemas.inventory_movement import (
    InventoryMovementCreate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class InventoryMovementService:

    # =====================================================
    # QUERY BASE
    # =====================================================

    @staticmethod
    def _base_query(
        db: Session,
    ):

        return (
            db.query(
                InventoryMovement
            )
            .join(
                Inventory,
                InventoryMovement.inventory_id
                ==
                Inventory.id,
            )
            .join(
                Branch,
                Inventory.branch_id
                ==
                Branch.id,
            )
            .join(
                ProductVariant,
                Inventory.product_variant_id
                ==
                ProductVariant.id,
            )
            .join(
                Product,
                ProductVariant.product_id
                ==
                Product.id,
            )
            .options(
                joinedload(
                    InventoryMovement.inventory
                )
                .joinedload(
                    Inventory.branch
                ),

                joinedload(
                    InventoryMovement.inventory
                )
                .joinedload(
                    Inventory.product_variant
                )
                .joinedload(
                    ProductVariant.product
                ),

                joinedload(
                    InventoryMovement.inventory
                )
                .joinedload(
                    Inventory.product_variant
                )
                .joinedload(
                    ProductVariant.size
                ),

                joinedload(
                    InventoryMovement.inventory
                )
                .joinedload(
                    Inventory.product_variant
                )
                .joinedload(
                    ProductVariant.color
                ),

                joinedload(
                    InventoryMovement.supplier
                ),

                joinedload(
                    InventoryMovement.user
                ),
            )
        )


    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_movements(
        db: Session,

        page: int = 1,

        page_size: int = 10,

        search: str | None = None,

        inventory_id: int | None = None,

        branch_id: int | None = None,

        product_id: int | None = None,

        product_variant_id: int | None = None,

        supplier_id: int | None = None,

        user_id: int | None = None,

        movement_type: str | None = None,

        sort_order: str = "desc",
    ) -> dict:

        page = max(
            page,
            1,
        )

        page_size = max(
            1,
            min(
                page_size,
                100,
            ),
        )


        query = (
            InventoryMovementService
            ._base_query(
                db
            )
        )


        # =================================================
        # BÚSQUEDA
        # =================================================

        if search:

            clean_search = (
                search.strip()
            )

            if clean_search:

                pattern = (
                    f"%{clean_search}%"
                )

                query = query.filter(
                    or_(
                        Branch.name.ilike(
                            pattern
                        ),

                        Product.name.ilike(
                            pattern
                        ),

                        Product.code.ilike(
                            pattern
                        ),

                        Product.brand.ilike(
                            pattern
                        ),

                        ProductVariant.sku.ilike(
                            pattern
                        ),

                        InventoryMovement
                        .reference_code
                        .ilike(
                            pattern
                        ),

                        InventoryMovement
                        .reason
                        .ilike(
                            pattern
                        ),
                    )
                )


        # =================================================
        # FILTROS
        # =================================================

        if inventory_id is not None:

            query = query.filter(
                InventoryMovement.inventory_id
                ==
                inventory_id
            )


        if branch_id is not None:

            query = query.filter(
                Inventory.branch_id
                ==
                branch_id
            )


        if product_id is not None:

            query = query.filter(
                ProductVariant.product_id
                ==
                product_id
            )


        if product_variant_id is not None:

            query = query.filter(
                Inventory.product_variant_id
                ==
                product_variant_id
            )


        if supplier_id is not None:

            query = query.filter(
                InventoryMovement.supplier_id
                ==
                supplier_id
            )


        if user_id is not None:

            query = query.filter(
                InventoryMovement.user_id
                ==
                user_id
            )


        if movement_type is not None:

            query = query.filter(
                InventoryMovement.movement_type
                ==
                movement_type
            )


        # =================================================
        # TOTAL
        # =================================================

        total = query.count()


        # =================================================
        # ORDEN
        # =================================================

        if (
            sort_order.lower()
            ==
            "asc"
        ):

            query = query.order_by(
                InventoryMovement.created_at.asc(),
                InventoryMovement.id.asc(),
            )

        else:

            query = query.order_by(
                InventoryMovement.created_at.desc(),
                InventoryMovement.id.desc(),
            )


        items = (
            query
            .offset(
                (page - 1)
                * page_size
            )
            .limit(
                page_size
            )
            .all()
        )


        total_pages = (
            math.ceil(
                total
                /
                page_size
            )
            if total > 0
            else 0
        )


        return {
            "items":
                items,

            "page":
                page,

            "page_size":
                page_size,

            "total":
                total,

            "total_pages":
                total_pages,
        }


    # =====================================================
    # OBTENER
    # =====================================================

    @staticmethod
    def get_movement(
        db: Session,

        movement_id: int,
    ) -> InventoryMovement:

        movement = (
            InventoryMovementService
            ._base_query(
                db
            )
            .filter(
                InventoryMovement.id
                ==
                movement_id
            )
            .first()
        )


        if movement is None:

            raise LookupError(
                "Movimiento de inventario no encontrado."
            )


        return movement


    # =====================================================
    # INVENTARIO BLOQUEADO
    # =====================================================

    @staticmethod
    def _get_inventory_for_update(
        db: Session,

        inventory_id: int,
    ) -> Inventory:

        inventory = (
            db.query(
                Inventory
            )
            .filter(
                Inventory.id
                ==
                inventory_id
            )
            .with_for_update()
            .first()
        )


        if inventory is None:

            raise LookupError(
                "Registro de inventario no encontrado."
            )


        if not inventory.is_active:

            raise ValueError(
                "No se pueden registrar movimientos "
                "sobre un inventario inactivo."
            )


        return inventory


    # =====================================================
    # VALIDAR PROVEEDOR GENÉRICO
    # =====================================================

    @staticmethod
    def _validate_supplier(
        db: Session,

        supplier_id: int | None,
    ) -> None:

        if supplier_id is None:

            return


        supplier = (
            db.get(
                Supplier,
                supplier_id,
            )
        )


        if supplier is None:

            raise LookupError(
                "Proveedor no encontrado."
            )


        if not supplier.is_active:

            raise ValueError(
                "El proveedor seleccionado está inactivo."
            )


    # =====================================================
    # DISPONIBILIDAD DEL PROVEEDOR PARA ENTRY
    # =====================================================

    @staticmethod
    def _get_supplier_availability_for_entry(
        db: Session,

        supplier_availability_id: int | None,

        inventory: Inventory,

        quantity: int,
    ) -> tuple[
        SupplierAvailability,
        SupplierProduct,
        int,
        object,
    ]:

        if supplier_availability_id is None:

            raise ValueError(
                "Para una entrada de inventario debes "
                "seleccionar un proveedor con disponibilidad."
            )


        availability = (
            db.query(
                SupplierAvailability
            )
            .filter(
                SupplierAvailability.id
                ==
                supplier_availability_id
            )
            .with_for_update()
            .first()
        )


        if availability is None:

            raise LookupError(
                "Disponibilidad del proveedor no encontrada."
            )


        supplier_product = (
            db.query(
                SupplierProduct
            )
            .filter(
                SupplierProduct.id
                ==
                availability.supplier_product_id
            )
            .first()
        )


        if supplier_product is None:

            raise LookupError(
                "Producto del proveedor no encontrado."
            )


        supplier = (
            db.get(
                Supplier,
                supplier_product.supplier_id,
            )
        )


        if supplier is None:

            raise LookupError(
                "Proveedor no encontrado."
            )


        if not supplier.is_active:

            raise ValueError(
                "El proveedor seleccionado está inactivo."
            )


        if not supplier_product.is_active:

            raise ValueError(
                "La asociación del producto con el "
                "proveedor está inactiva."
            )


        # Debe ser exactamente la variante del inventario.
        if (
            availability.product_variant_id
            !=
            inventory.product_variant_id
        ):

            raise ValueError(
                "El proveedor seleccionado no tiene "
                "disponibilidad para la variante "
                "del inventario."
            )


        if (
            availability.available_quantity
            <=
            0
        ):

            raise ValueError(
                "El proveedor ya no tiene unidades "
                "disponibles de esta variante."
            )


        if (
            availability.status
            ==
            "OUT_OF_STOCK"
        ):

            raise ValueError(
                "La disponibilidad del proveedor "
                "se encuentra sin stock."
            )


        if (
            quantity
            >
            availability.available_quantity
        ):

            raise ValueError(
                "La cantidad solicitada supera la "
                "disponibilidad del proveedor. "
                f"Máximo disponible: "
                f"{availability.available_quantity}."
            )


        # Precio específico de variante.
        effective_price = (
            availability.purchase_price
        )


        # Si la variante no tiene precio propio,
        # utilizamos el precio general del producto
        # registrado en CU18.
        if effective_price is None:

            effective_price = (
                supplier_product.purchase_price
            )


        if effective_price is None:

            raise ValueError(
                "El producto del proveedor no tiene "
                "un precio de compra configurado."
            )


        return (
            availability,
            supplier_product,
            supplier.id,
            effective_price,
        )


    # =====================================================
    # CALCULAR MOVIMIENTO
    # =====================================================

    @staticmethod
    def _calculate_after_values(
        inventory: Inventory,

        movement_type: str,

        quantity: int,
    ) -> tuple[int, int]:

        stock_before = (
            inventory.stock_quantity
        )

        reserved_before = (
            inventory.reserved_quantity
        )


        stock_after = (
            stock_before
        )

        reserved_after = (
            reserved_before
        )


        if movement_type in {
            "ENTRY",
            "ADJUSTMENT_IN",
            "RETURN_IN",
            "TRANSFER_IN",
        }:

            stock_after += (
                quantity
            )


        elif movement_type in {
            "SALE",
            "ADJUSTMENT_OUT",
            "RETURN_OUT",
            "TRANSFER_OUT",
        }:

            if (
                quantity
                >
                (
                    stock_before
                    -
                    reserved_before
                )
            ):

                raise ValueError(
                    "No existe stock disponible suficiente "
                    "para realizar este movimiento."
                )


            stock_after -= (
                quantity
            )


        elif movement_type == "RESERVE":

            available_quantity = (
                stock_before
                -
                reserved_before
            )


            if (
                quantity
                >
                available_quantity
            ):

                raise ValueError(
                    "No existe stock disponible suficiente "
                    "para realizar la reserva."
                )


            reserved_after += (
                quantity
            )


        elif movement_type == "RELEASE":

            if (
                quantity
                >
                reserved_before
            ):

                raise ValueError(
                    "No se puede liberar una cantidad "
                    "mayor a la actualmente reservada."
                )


            reserved_after -= (
                quantity
            )


        else:

            raise ValueError(
                "Tipo de movimiento no válido."
            )


        if stock_after < 0:

            raise ValueError(
                "El stock resultante no puede ser negativo."
            )


        if reserved_after < 0:

            raise ValueError(
                "La cantidad reservada resultante "
                "no puede ser negativa."
            )


        if (
            reserved_after
            >
            stock_after
        ):

            raise ValueError(
                "La cantidad reservada resultante "
                "no puede superar el stock."
            )


        if (
            inventory.maximum_stock
            is not None
            and
            stock_after
            >
            inventory.maximum_stock
        ):

            raise ValueError(
                "El movimiento supera el stock máximo "
                "configurado para este inventario."
            )


        return (
            stock_after,
            reserved_after,
        )


    # =====================================================
    # CREAR MOVIMIENTO
    # =====================================================

    @staticmethod
    def create_movement(
        db: Session,

        payload:
            InventoryMovementCreate,

        user_id:
            int | None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> InventoryMovement:

        try:

            inventory = (
                InventoryMovementService
                ._get_inventory_for_update(
                    db=db,

                    inventory_id=
                        payload.inventory_id,
                )
            )


            supplier_id = (
                payload.supplier_id
            )

            unit_cost = (
                payload.unit_cost
            )

            supplier_availability = (
                None
            )


            # =================================================
            # ENTRY VINCULADO A CU18/CU19
            # =================================================

            if (
                payload.movement_type
                ==
                "ENTRY"
            ):

                (
                    supplier_availability,
                    supplier_product,
                    supplier_id,
                    unit_cost,
                ) = (
                    InventoryMovementService
                    ._get_supplier_availability_for_entry(
                        db=db,

                        supplier_availability_id=
                            payload
                            .supplier_availability_id,

                        inventory=
                            inventory,

                        quantity=
                            payload.quantity,
                    )
                )

            else:

                InventoryMovementService \
                    ._validate_supplier(
                        db=db,

                        supplier_id=
                            supplier_id,
                    )


            stock_before = (
                inventory.stock_quantity
            )

            reserved_before = (
                inventory.reserved_quantity
            )


            (
                stock_after,
                reserved_after,
            ) = (
                InventoryMovementService
                ._calculate_after_values(
                    inventory=
                        inventory,

                    movement_type=
                        payload.movement_type,

                    quantity=
                        payload.quantity,
                )
            )


            # =================================================
            # ACTUALIZAR INVENTARIO
            # =================================================

            inventory.stock_quantity = (
                stock_after
            )

            inventory.reserved_quantity = (
                reserved_after
            )


            # =================================================
            # DESCONTAR DISPONIBILIDAD DEL PROVEEDOR
            # =================================================

            if (
                payload.movement_type
                ==
                "ENTRY"
                and
                supplier_availability
                is not None
            ):

                supplier_availability \
                    .available_quantity -= (
                        payload.quantity
                    )


                if (
                    supplier_availability
                    .available_quantity
                    ==
                    0
                ):

                    supplier_availability.status = (
                        "OUT_OF_STOCK"
                    )


                supplier_availability.last_checked_at = (
                    datetime.now(
                        timezone.utc
                    )
                )


            # =================================================
            # CREAR HISTORIAL
            # =================================================

            movement = InventoryMovement(
                inventory_id=
                    inventory.id,

                movement_type=
                    payload.movement_type,

                quantity=
                    payload.quantity,

                stock_before=
                    stock_before,

                stock_after=
                    stock_after,

                reserved_before=
                    reserved_before,

                reserved_after=
                    reserved_after,

                supplier_id=
                    supplier_id,

                user_id=
                    user_id,

                unit_cost=
                    unit_cost,

                reference_type=
                    (
                        payload.reference_type.strip()
                        if payload.reference_type
                        else None
                    ),

                reference_id=
                    payload.reference_id,

                reference_code=
                    (
                        payload.reference_code.strip()
                        if payload.reference_code
                        else None
                    ),

                reason=
                    (
                        payload.reason.strip()
                        if payload.reason
                        else None
                    ),

                notes=
                    (
                        payload.notes.strip()
                        if payload.notes
                        else None
                    ),
            )


            db.add(
                movement
            )

            db.flush()


            # =================================================
            # AUDITORÍA
            # =================================================

            new_values = {
                "stock_quantity":
                    stock_after,

                "reserved_quantity":
                    reserved_after,

                "movement_type":
                    movement.movement_type,

                "quantity":
                    movement.quantity,

                "supplier_id":
                    supplier_id,

                "unit_cost":
                    (
                        str(unit_cost)
                        if unit_cost
                        is not None
                        else None
                    ),
            }


            if (
                supplier_availability
                is not None
            ):

                new_values[
                    "supplier_availability_id"
                ] = (
                    supplier_availability.id
                )

                new_values[
                    "supplier_available_quantity"
                ] = (
                    supplier_availability
                    .available_quantity
                )


            AuditLogService.log(
                db=db,

                user_id=
                    user_id,

                action=
                    "CREATE_INVENTORY_MOVEMENT",

                module=
                    "INVENTORY",

                entity_type=
                    "InventoryMovement",

                entity_id=
                    movement.id,

                description=(
                    f"Se registró movimiento "
                    f"{movement.movement_type} "
                    f"por {movement.quantity} unidad(es)."
                ),

                old_values={
                    "stock_quantity":
                        stock_before,

                    "reserved_quantity":
                        reserved_before,
                },

                new_values=
                    new_values,

                ip_address=
                    ip_address,

                user_agent=
                    user_agent,

                status=
                    "SUCCESS",
            )


            db.commit()


            return (
                InventoryMovementService
                .get_movement(
                    db=db,

                    movement_id=
                        movement.id,
                )
            )


        except Exception:

            db.rollback()

            raise