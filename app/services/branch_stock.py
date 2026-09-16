from __future__ import annotations

import math

from sqlalchemy import (
    func,
    or_,
)

from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.branch import Branch

from app.models.inventory import Inventory

from app.models.product import Product

from app.models.product_variant import (
    ProductVariant,
)

from app.models.user import User

from app.services.branch_service import (
    BranchService,
)


class BranchStockService:

    ADMIN_ROLES = {
        "ADMINISTRADOR",
        "SUPERADMIN",
    }

    BRANCH_ROLES = {
        "ENCARGADO_SUCURSAL",
        "CAJERO",
    }

    # =====================================================
    # RESOLVER SUCURSAL SEGÚN ROL
    # =====================================================

    @staticmethod
    def _resolve_branch_scope(
        db: Session,
        current_user: User,
        requested_branch_id: int | None = None,
    ) -> int | None:

        role = (
            current_user.role.name.strip().upper()
            if current_user.role is not None
            else ""
        )

        if role in BranchStockService.ADMIN_ROLES:
            return requested_branch_id

        if role in BranchStockService.BRANCH_ROLES:

            branch = BranchService.get_my_branch(
                db=db,
                user_id=current_user.id,
            )

            if (
                requested_branch_id is not None
                and
                requested_branch_id != branch.id
            ):
                raise PermissionError(
                    "No puedes consultar existencias "
                    "de otra sucursal."
                )

            return branch.id

        raise PermissionError(
            "Tu rol no puede consultar existencias "
            "por sucursal."
        )


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
                    ProductVariant.product
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
            )
        )


    # =====================================================
    # LISTAR EXISTENCIAS
    # =====================================================

    @staticmethod
    def get_branch_stock(
        db: Session,

        current_user: User,

        page: int = 1,

        page_size: int = 10,

        search: str | None = None,

        branch_id: int | None = None,

        product_id: int | None = None,

        product_variant_id: int | None = None,

        low_stock: bool | None = None,

        out_of_stock: bool | None = None,

        is_active: bool | None = True,

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


        effective_branch_id = (
            BranchStockService
            ._resolve_branch_scope(
                db=db,
                current_user=current_user,
                requested_branch_id=branch_id,
            )
        )


        query = (
            BranchStockService
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

                        Product.code.ilike(
                            pattern
                        ),

                        Product.name.ilike(
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
        # SUCURSAL
        # =================================================

        if effective_branch_id is not None:

            query = query.filter(
                Inventory.branch_id
                ==
                effective_branch_id
            )


        # =================================================
        # PRODUCTO
        # =================================================

        if product_id is not None:

            query = query.filter(
                ProductVariant.product_id
                ==
                product_id
            )


        # =================================================
        # VARIANTE
        # =================================================

        if product_variant_id is not None:

            query = query.filter(
                Inventory.product_variant_id
                ==
                product_variant_id
            )


        # =================================================
        # ACTIVO
        # =================================================

        if is_active is not None:

            query = query.filter(
                Inventory.is_active
                ==
                is_active
            )


        # =================================================
        # STOCK BAJO
        # =================================================

        available_expression = (
            Inventory.stock_quantity
            -
            Inventory.reserved_quantity
        )


        if low_stock is True:

            query = query.filter(
                available_expression
                <=
                Inventory.reorder_point
            )


        if low_stock is False:

            query = query.filter(
                available_expression
                >
                Inventory.reorder_point
            )


        # =================================================
        # SIN STOCK
        # =================================================

        if out_of_stock is True:

            query = query.filter(
                available_expression
                ==
                0
            )


        if out_of_stock is False:

            query = query.filter(
                available_expression
                >
                0
            )


        # =================================================
        # RESUMEN ANTES DE PAGINAR
        # =================================================

        filtered_items = (
            query.all()
        )


        total_stock = sum(
            item.stock_quantity
            for item in filtered_items
        )


        total_reserved = sum(
            item.reserved_quantity
            for item in filtered_items
        )


        total_available = sum(
            item.available_quantity
            for item in filtered_items
        )


        low_stock_records = sum(
            1
            for item in filtered_items
            if item.is_low_stock
        )


        out_of_stock_records = sum(
            1
            for item in filtered_items
            if item.available_quantity == 0
        )


        total = len(
            filtered_items
        )


        # =================================================
        # ORDENAMIENTO
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

            "available_quantity":
                available_expression,

            "minimum_stock":
                Inventory.minimum_stock,

            "maximum_stock":
                Inventory.maximum_stock,

            "reorder_point":
                Inventory.reorder_point,

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

        records = (
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


        items = [
            {
                "inventory_id":
                    item.id,

                "branch_id":
                    item.branch_id,

                "product_variant_id":
                    item.product_variant_id,

                "stock_quantity":
                    item.stock_quantity,

                "reserved_quantity":
                    item.reserved_quantity,

                "available_quantity":
                    item.available_quantity,

                "minimum_stock":
                    item.minimum_stock,

                "maximum_stock":
                    item.maximum_stock,

                "reorder_point":
                    item.reorder_point,

                "is_low_stock":
                    item.is_low_stock,

                "is_active":
                    item.is_active,

                "updated_at":
                    item.updated_at,

                "branch":
                    item.branch,

                "product_variant":
                    item.product_variant,
            }

            for item in records
        ]


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

            "summary": {
                "total_records":
                    total,

                "total_stock":
                    total_stock,

                "total_reserved":
                    total_reserved,

                "total_available":
                    total_available,

                "low_stock_records":
                    low_stock_records,

                "out_of_stock_records":
                    out_of_stock_records,
            },

            "page":
                page,

            "page_size":
                page_size,

            "total":
                total,

            "total_pages":
                total_pages,
        }