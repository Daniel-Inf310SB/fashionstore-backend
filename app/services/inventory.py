from __future__ import annotations

import math

from sqlalchemy import (
    or_,
)

from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.branch import Branch

from app.models.inventory import Inventory

from app.models.product import Product

from app.models.product_variant import ProductVariant

from app.schemas.inventory import (
    InventoryCreate,
    InventoryUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class InventoryService:

    # =====================================================
    # QUERY BASE
    # =====================================================

    @staticmethod
    def _base_query(
        db: Session,
    ):

        return (
            db.query(
                Inventory
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
                    Inventory.branch
                ),

                joinedload(
                    Inventory.product_variant
                )
                .joinedload(
                    ProductVariant.size
                ),

                joinedload(
                    Inventory.product_variant
                )
                .joinedload(
                    ProductVariant.color
                ),

                joinedload(
                    Inventory.product_variant
                )
                .joinedload(
                    ProductVariant.product
                ),
            )
        )


    # =====================================================
    # OBTENER SUCURSAL
    # =====================================================

    @staticmethod
    def _get_branch(
        db: Session,
        branch_id: int,
    ) -> Branch:

        branch = (
            db.get(
                Branch,
                branch_id,
            )
        )

        if branch is None:

            raise LookupError(
                "Sucursal no encontrada."
            )

        return branch


    # =====================================================
    # OBTENER VARIANTE
    # =====================================================

    @staticmethod
    def _get_variant(
        db: Session,
        product_variant_id: int,
    ) -> ProductVariant:

        variant = (
            db.get(
                ProductVariant,
                product_variant_id,
            )
        )

        if variant is None:

            raise LookupError(
                "Variante de producto no encontrada."
            )

        return variant


    # =====================================================
    # VALIDAR DUPLICADO
    # =====================================================

    @staticmethod
    def _validate_unique_inventory(
        db: Session,

        branch_id: int,

        product_variant_id: int,
    ) -> None:

        existing = (
            db.query(
                Inventory
            )
            .filter(
                Inventory.branch_id
                ==
                branch_id,

                Inventory.product_variant_id
                ==
                product_variant_id,
            )
            .first()
        )

        if existing is not None:

            raise ValueError(
                "Ya existe inventario para esta "
                "variante en la sucursal seleccionada."
            )


    # =====================================================
    # VALIDAR STOCK
    # =====================================================

    @staticmethod
    def _validate_stock_values(
        stock_quantity: int,

        reserved_quantity: int,

        minimum_stock: int,

        maximum_stock: int | None,

        reorder_point: int,
    ) -> None:

        if (
            reserved_quantity
            >
            stock_quantity
        ):

            raise ValueError(
                "La cantidad reservada no puede "
                "ser mayor al stock físico."
            )


        if (
            maximum_stock is not None
            and
            maximum_stock
            <
            minimum_stock
        ):

            raise ValueError(
                "El stock máximo no puede ser "
                "menor al stock mínimo."
            )


        if (
            maximum_stock is not None
            and
            stock_quantity
            >
            maximum_stock
        ):

            raise ValueError(
                "El stock inicial no puede superar "
                "el stock máximo configurado."
            )


        if (
            reorder_point
            >
            (
                maximum_stock
                if maximum_stock is not None
                else max(
                    stock_quantity,
                    minimum_stock,
                    reorder_point,
                )
            )
            and
            maximum_stock is not None
        ):

            raise ValueError(
                "El punto de reposición no puede "
                "superar el stock máximo."
            )


    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_inventories(
        db: Session,

        page: int = 1,

        page_size: int = 10,

        search: str | None = None,

        branch_id: int | None = None,

        product_id: int | None = None,

        product_variant_id: int | None = None,

        is_active: bool | None = None,

        low_stock: bool | None = None,

        sort_by: str = "updated_at",

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
            InventoryService
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
                    )
                )


        # =================================================
        # FILTROS
        # =================================================

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


        if is_active is not None:

            query = query.filter(
                Inventory.is_active
                ==
                is_active
            )


        if low_stock is True:

            query = query.filter(
                (
                    Inventory.stock_quantity
                    -
                    Inventory.reserved_quantity
                )
                <=
                Inventory.reorder_point
            )


        if low_stock is False:

            query = query.filter(
                (
                    Inventory.stock_quantity
                    -
                    Inventory.reserved_quantity
                )
                >
                Inventory.reorder_point
            )


        # =================================================
        # TOTAL
        # =================================================

        total = query.count()


        # =================================================
        # ORDEN
        # =================================================

        sort_columns = {
            "id":
                Inventory.id,

            "branch_id":
                Inventory.branch_id,

            "product_variant_id":
                Inventory.product_variant_id,

            "stock_quantity":
                Inventory.stock_quantity,

            "reserved_quantity":
                Inventory.reserved_quantity,

            "minimum_stock":
                Inventory.minimum_stock,

            "maximum_stock":
                Inventory.maximum_stock,

            "reorder_point":
                Inventory.reorder_point,

            "is_active":
                Inventory.is_active,

            "created_at":
                Inventory.created_at,

            "updated_at":
                Inventory.updated_at,
        }


        sort_column = (
            sort_columns.get(
                sort_by,
                Inventory.updated_at,
            )
        )


        if (
            sort_order.lower()
            ==
            "asc"
        ):

            query = query.order_by(
                sort_column.asc(),
                Inventory.id.asc(),
            )

        else:

            query = query.order_by(
                sort_column.desc(),
                Inventory.id.desc(),
            )


        # =================================================
        # PAGINACIÓN
        # =================================================

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
    def get_inventory(
        db: Session,

        inventory_id: int,
    ) -> Inventory:

        inventory = (
            InventoryService
            ._base_query(
                db
            )
            .filter(
                Inventory.id
                ==
                inventory_id
            )
            .first()
        )


        if inventory is None:

            raise LookupError(
                "Registro de inventario no encontrado."
            )


        return inventory


    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_inventory(
        db: Session,

        payload:
            InventoryCreate,

        user_id:
            int | None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> Inventory:

        branch = (
            InventoryService
            ._get_branch(
                db=db,

                branch_id=
                    payload.branch_id,
            )
        )


        variant = (
            InventoryService
            ._get_variant(
                db=db,

                product_variant_id=
                    payload.product_variant_id,
            )
        )


        if not variant.is_active:

            raise ValueError(
                "La variante seleccionada "
                "se encuentra inactiva."
            )


        InventoryService \
            ._validate_unique_inventory(
                db=db,

                branch_id=
                    payload.branch_id,

                product_variant_id=
                    payload.product_variant_id,
            )


        InventoryService \
            ._validate_stock_values(
                stock_quantity=
                    payload.stock_quantity,

                reserved_quantity=
                    payload.reserved_quantity,

                minimum_stock=
                    payload.minimum_stock,

                maximum_stock=
                    payload.maximum_stock,

                reorder_point=
                    payload.reorder_point,
            )


        inventory = Inventory(
            branch_id=
                payload.branch_id,

            product_variant_id=
                payload.product_variant_id,

            stock_quantity=
                payload.stock_quantity,

            reserved_quantity=
                payload.reserved_quantity,

            minimum_stock=
                payload.minimum_stock,

            maximum_stock=
                payload.maximum_stock,

            reorder_point=
                payload.reorder_point,

            is_active=
                True,
        )


        db.add(
            inventory
        )

        db.flush()


        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "CREATE_INVENTORY",

            module=
                "INVENTORY",

            entity_type=
                "Inventory",

            entity_id=
                inventory.id,

            description=(
                "Se creó un registro "
                "de inventario."
            ),

            old_values=None,

            new_values={
                "branch_id":
                    inventory.branch_id,

                "product_variant_id":
                    inventory
                    .product_variant_id,

                "stock_quantity":
                    inventory
                    .stock_quantity,

                "reserved_quantity":
                    inventory
                    .reserved_quantity,

                "minimum_stock":
                    inventory
                    .minimum_stock,

                "maximum_stock":
                    inventory
                    .maximum_stock,

                "reorder_point":
                    inventory
                    .reorder_point,

                "is_active":
                    inventory.is_active,
            },

            ip_address=
                ip_address,

            user_agent=
                user_agent,

            status=
                "SUCCESS",
        )


        db.commit()


        return (
            InventoryService
            .get_inventory(
                db=db,

                inventory_id=
                    inventory.id,
            )
        )


    # =====================================================
    # ACTUALIZAR CONFIGURACIÓN
    # =====================================================

    @staticmethod
    def update_inventory(
        db: Session,

        inventory_id: int,

        payload:
            InventoryUpdate,

        user_id:
            int | None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> Inventory:

        inventory = (
            InventoryService
            .get_inventory(
                db=db,

                inventory_id=
                    inventory_id,
            )
        )


        old_values = {
            "minimum_stock":
                inventory.minimum_stock,

            "maximum_stock":
                inventory.maximum_stock,

            "reorder_point":
                inventory.reorder_point,

            "is_active":
                inventory.is_active,
        }


        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )


        final_minimum = (
            update_data.get(
                "minimum_stock",
                inventory.minimum_stock,
            )
        )


        final_maximum = (
            update_data.get(
                "maximum_stock",
                inventory.maximum_stock,
            )
        )


        final_reorder = (
            update_data.get(
                "reorder_point",
                inventory.reorder_point,
            )
        )


        InventoryService \
            ._validate_stock_values(
                stock_quantity=
                    inventory.stock_quantity,

                reserved_quantity=
                    inventory.reserved_quantity,

                minimum_stock=
                    final_minimum,

                maximum_stock=
                    final_maximum,

                reorder_point=
                    final_reorder,
            )


        if (
            "minimum_stock"
            in update_data
            and
            update_data[
                "minimum_stock"
            ] is not None
        ):

            inventory.minimum_stock = (
                update_data[
                    "minimum_stock"
                ]
            )


        if (
            "maximum_stock"
            in update_data
        ):

            inventory.maximum_stock = (
                update_data[
                    "maximum_stock"
                ]
            )


        if (
            "reorder_point"
            in update_data
            and
            update_data[
                "reorder_point"
            ] is not None
        ):

            inventory.reorder_point = (
                update_data[
                    "reorder_point"
                ]
            )


        if (
            "is_active"
            in update_data
            and
            update_data[
                "is_active"
            ] is not None
        ):

            inventory.is_active = (
                update_data[
                    "is_active"
                ]
            )


        db.flush()


        new_values = {
            "minimum_stock":
                inventory.minimum_stock,

            "maximum_stock":
                inventory.maximum_stock,

            "reorder_point":
                inventory.reorder_point,

            "is_active":
                inventory.is_active,
        }


        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_INVENTORY",

            module=
                "INVENTORY",

            entity_type=
                "Inventory",

            entity_id=
                inventory.id,

            description=(
                "Se actualizó la configuración "
                "del inventario."
            ),

            old_values=
                old_values,

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
            InventoryService
            .get_inventory(
                db=db,

                inventory_id=
                    inventory.id,
            )
        )


    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_inventory(
        db: Session,

        inventory_id: int,

        user_id:
            int | None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> Inventory:

        inventory = (
            InventoryService
            .get_inventory(
                db=db,

                inventory_id=
                    inventory_id,
            )
        )


        if not inventory.is_active:

            return inventory


        old_values = {
            "is_active":
                inventory.is_active,
        }


        inventory.is_active = False

        db.flush()


        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "DEACTIVATE_INVENTORY",

            module=
                "INVENTORY",

            entity_type=
                "Inventory",

            entity_id=
                inventory.id,

            description=(
                "Se desactivó un registro "
                "de inventario."
            ),

            old_values=
                old_values,

            new_values={
                "is_active":
                    False,
            },

            ip_address=
                ip_address,

            user_agent=
                user_agent,

            status=
                "SUCCESS",
        )


        db.commit()


        return (
            InventoryService
            .get_inventory(
                db=db,

                inventory_id=
                    inventory.id,
            )
        )