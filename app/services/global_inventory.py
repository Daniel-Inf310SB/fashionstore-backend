from __future__ import annotations

import math

from sqlalchemy import (
    case,
    func,
    or_,
)

from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.branch import (
    Branch,
)

from app.models.inventory import (
    Inventory,
)

from app.models.product import (
    Product,
)

from app.models.product_variant import (
    ProductVariant,
)


class GlobalInventoryService:

    # =====================================================
    # QUERY FILTRADA BASE
    # =====================================================

    @staticmethod
    def _filtered_query(
        db: Session,

        search: str | None = None,

        branch_id: int | None = None,

        product_id: int | None = None,

        product_variant_id:
            int | None = None,

        is_active:
            bool | None = True,
    ):

        query = (
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

                        Branch.name.ilike(
                            pattern
                        ),
                    )
                )


        # =================================================
        # SUCURSAL
        # =================================================

        if branch_id is not None:

            query = query.filter(
                Inventory.branch_id
                ==
                branch_id
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

        if (
            product_variant_id
            is not None
        ):

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


        return query


    # =====================================================
    # CONSULTAR INVENTARIO GLOBAL
    # =====================================================

    @staticmethod
    def get_global_inventory(
        db: Session,

        page: int = 1,

        page_size: int = 20,

        search: str | None = None,

        branch_id: int | None = None,

        product_id: int | None = None,

        product_variant_id:
            int | None = None,

        is_active:
            bool | None = True,

        low_stock:
            bool | None = None,

        out_of_stock:
            bool | None = None,

        sort_by:
            str = "total_available",

        sort_order:
            str = "desc",
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


        base_query = (
            GlobalInventoryService
            ._filtered_query(
                db=db,

                search=search,

                branch_id=
                    branch_id,

                product_id=
                    product_id,

                product_variant_id=
                    product_variant_id,

                is_active=
                    is_active,
            )
        )


        available_expression = (
            Inventory.stock_quantity
            -
            Inventory.reserved_quantity
        )


        low_stock_case = case(
            (
                available_expression
                <=
                Inventory.reorder_point,

                1,
            ),

            else_=0,
        )


        out_of_stock_case = case(
            (
                available_expression
                <=
                0,

                1,
            ),

            else_=0,
        )


        # =================================================
        # AGREGAR POR VARIANTE
        # =================================================

        grouped_query = (
            base_query
            .with_entities(
                Inventory
                .product_variant_id
                .label(
                    "product_variant_id"
                ),

                func.count(
                    func.distinct(
                        Inventory.branch_id
                    )
                )
                .label(
                    "branch_count"
                ),

                func.coalesce(
                    func.sum(
                        Inventory.stock_quantity
                    ),
                    0,
                )
                .label(
                    "total_stock"
                ),

                func.coalesce(
                    func.sum(
                        Inventory.reserved_quantity
                    ),
                    0,
                )
                .label(
                    "total_reserved"
                ),

                func.coalesce(
                    func.sum(
                        available_expression
                    ),
                    0,
                )
                .label(
                    "total_available"
                ),

                func.coalesce(
                    func.sum(
                        low_stock_case
                    ),
                    0,
                )
                .label(
                    "low_stock_branches"
                ),

                func.coalesce(
                    func.sum(
                        out_of_stock_case
                    ),
                    0,
                )
                .label(
                    "out_of_stock_branches"
                ),

                func.max(
                    Inventory.updated_at
                )
                .label(
                    "last_updated_at"
                ),
            )
            .group_by(
                Inventory.product_variant_id
            )
        )


        # =================================================
        # FILTROS DE RESULTADO GLOBAL
        # =================================================

        if low_stock is True:

            grouped_query = (
                grouped_query.having(
                    func.sum(
                        low_stock_case
                    )
                    >
                    0
                )
            )


        elif low_stock is False:

            grouped_query = (
                grouped_query.having(
                    func.sum(
                        low_stock_case
                    )
                    ==
                    0
                )
            )


        if out_of_stock is True:

            grouped_query = (
                grouped_query.having(
                    func.sum(
                        out_of_stock_case
                    )
                    >
                    0
                )
            )


        elif out_of_stock is False:

            grouped_query = (
                grouped_query.having(
                    func.sum(
                        out_of_stock_case
                    )
                    ==
                    0
                )
            )


        # =================================================
        # OBTENER TODOS LOS GRUPOS PARA RESUMEN
        # =================================================

        all_groups = (
            grouped_query.all()
        )


        total = (
            len(
                all_groups
            )
        )


        # =================================================
        # RESUMEN GLOBAL
        # =================================================

        total_stock = sum(
            int(
                item.total_stock
                or
                0
            )
            for item in all_groups
        )


        total_reserved = sum(
            int(
                item.total_reserved
                or
                0
            )
            for item in all_groups
        )


        total_available = sum(
            int(
                item.total_available
                or
                0
            )
            for item in all_groups
        )


        low_stock_variants = sum(
            1
            for item in all_groups
            if int(
                item.low_stock_branches
                or
                0
            )
            >
            0
        )


        out_of_stock_variants = sum(
            1
            for item in all_groups
            if int(
                item.out_of_stock_branches
                or
                0
            )
            >
            0
        )


        low_stock_branch_records = sum(
            int(
                item.low_stock_branches
                or
                0
            )
            for item in all_groups
        )


        out_of_stock_branch_records = sum(
            int(
                item.out_of_stock_branches
                or
                0
            )
            for item in all_groups
        )


        # =================================================
        # ORDEN
        # =================================================

        sort_map = {
            "product_variant_id":
                "product_variant_id",

            "branch_count":
                "branch_count",

            "total_stock":
                "total_stock",

            "total_reserved":
                "total_reserved",

            "total_available":
                "total_available",

            "low_stock_branches":
                "low_stock_branches",

            "out_of_stock_branches":
                "out_of_stock_branches",

            "last_updated_at":
                "last_updated_at",
        }


        valid_sort = (
            sort_map.get(
                sort_by,
                "total_available",
            )
        )


        reverse = (
            sort_order.lower()
            ==
            "desc"
        )


        sorted_groups = sorted(
            all_groups,

            key=lambda item:
                (
                    getattr(
                        item,
                        valid_sort,
                    )
                    if getattr(
                        item,
                        valid_sort,
                    )
                    is not None
                    else 0
                ),

            reverse=
                reverse,
        )


        # =================================================
        # PAGINACIÓN
        # =================================================

        start = (
            (page - 1)
            *
            page_size
        )


        end = (
            start
            +
            page_size
        )


        paginated_groups = (
            sorted_groups[
                start:end
            ]
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


        # =================================================
        # CARGAR VARIANTES
        # =================================================

        variant_ids = [
            item.product_variant_id
            for item
            in paginated_groups
        ]


        variants = []


        if variant_ids:

            variants = (
                db.query(
                    ProductVariant
                )
                .filter(
                    ProductVariant.id.in_(
                        variant_ids
                    )
                )
                .options(
                    joinedload(
                        ProductVariant.product
                    ),

                    joinedload(
                        ProductVariant.size
                    ),

                    joinedload(
                        ProductVariant.color
                    ),
                )
                .all()
            )


        variants_map = {
            variant.id:
                variant
            for variant
            in variants
        }


        # =================================================
        # ARMAR ITEMS
        # =================================================

        items = []


        for row in paginated_groups:

            low_stock_branches = int(
                row.low_stock_branches
                or
                0
            )


            out_of_stock_branches = int(
                row.out_of_stock_branches
                or
                0
            )


            variant = (
                variants_map.get(
                    row.product_variant_id
                )
            )


            if variant is None:

                continue


            items.append({
                "product_variant_id":
                    row.product_variant_id,

                "branch_count":
                    int(
                        row.branch_count
                        or
                        0
                    ),

                "total_stock":
                    int(
                        row.total_stock
                        or
                        0
                    ),

                "total_reserved":
                    int(
                        row.total_reserved
                        or
                        0
                    ),

                "total_available":
                    int(
                        row.total_available
                        or
                        0
                    ),

                "low_stock_branches":
                    low_stock_branches,

                "out_of_stock_branches":
                    out_of_stock_branches,

                "is_low_stock":
                    (
                        low_stock_branches
                        >
                        0
                    ),

                "is_out_of_stock":
                    (
                        int(
                            row.total_available
                            or
                            0
                        )
                        <=
                        0
                    ),

                "last_updated_at":
                    row.last_updated_at,

                "product_variant":
                    variant,
            })


        # =================================================
        # RESPONSE
        # =================================================

        return {
            "items":
                items,

            "summary": {
                "total_variants":
                    total,

                "total_stock":
                    total_stock,

                "total_reserved":
                    total_reserved,

                "total_available":
                    total_available,

                "low_stock_variants":
                    low_stock_variants,

                "out_of_stock_variants":
                    out_of_stock_variants,

                "low_stock_branch_records":
                    low_stock_branch_records,

                "out_of_stock_branch_records":
                    out_of_stock_branch_records,
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