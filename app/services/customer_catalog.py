import math

from datetime import (
    datetime,
    timezone,
)

from decimal import Decimal

from sqlalchemy import (
    func,
    or_,
)

from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.audience import (
    Audience,
)

from app.models.branch import (
    Branch,
)

from app.models.category import (
    Category,
)

from app.models.color import (
    Color,
)

from app.models.collection import (
    Collection,
)

from app.models.inventory import (
    Inventory,
)

from app.models.product import (
    Product,
)

from app.models.product_promotion import (
    ProductPromotion,
)

from app.models.product_collection import (
    ProductCollection,
)

from app.models.product_season import (
    ProductSeason,
)

from app.models.product_variant import (
    ProductVariant,
)

from app.models.promotion import (
    Promotion,
)

from app.models.size import (
    Size,
)

from app.models.season import (
    Season,
)

from app.services.customer_pricing import (
    CustomerPricingService,
)


class CustomerCatalogService:

    # =====================================================
    # CU24 + CU25
    # CONSULTAR CATÁLOGO / BUSCAR Y FILTRAR PRENDAS
    # =====================================================

    @staticmethod
    def get_catalog(
        db: Session,

        page: int = 1,

        page_size: int = 12,

        branch_id: int | None = None,

        search: str | None = None,

        audience: str | None = None,

        category: str | None = None,

        size_id: int | None = None,

        color_id: int | None = None,

        min_price: Decimal | None = None,

        max_price: Decimal | None = None,

        promotion: bool | None = None,

        promotion_id: int | None = None,

        collection_id: int | None = None,

        season_id: int | None = None,

        in_stock: bool | None = None,

        sort_by: str = "name",

        sort_order: str = "asc",
    ) -> dict:

        # =================================================
        # PAGINACIÓN
        # =================================================

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


        # =================================================
        # QUERY BASE
        # =================================================

        query = (
            db.query(
                Product
            )
            .join(
                Category,
                Product.category_id
                == Category.id,
            )
            .join(
                Audience,
                Product.audience_id
                == Audience.id,
            )
            .options(
                joinedload(
                    Product.category
                ),
                joinedload(
                    Product.audience
                ),
            )
            .filter(
                Product.is_active.is_(
                    True
                ),

                Category.is_active.is_(
                    True
                ),

                Audience.is_active.is_(
                    True
                ),
            )
        )


        # =================================================
        # AL MENOS UNA VARIANTE ACTIVA
        # =================================================

        active_variant_exists = (
            db.query(
                ProductVariant.id
            )
            .filter(
                ProductVariant.product_id
                == Product.id,

                ProductVariant.is_active.is_(
                    True
                ),
            )
            .exists()
        )


        query = query.filter(
            active_variant_exists
        )


        # =================================================
        # BÚSQUEDA DE PRENDAS
        # =================================================

        if (
            search
            and
            search.strip()
        ):

            normalized_search = (
                search.strip()
            )

            search_value = (
                f"%{normalized_search}%"
            )


            # =============================================
            # BUSCAR TAMBIÉN EN SKU
            # =============================================

            variant_search_exists = (
                db.query(
                    ProductVariant.id
                )
                .filter(
                    ProductVariant.product_id
                    == Product.id,

                    ProductVariant.is_active.is_(
                        True
                    ),

                    ProductVariant.sku.ilike(
                        search_value
                    ),
                )
                .exists()
            )


            query = query.filter(
                or_(
                    Product.name.ilike(
                        search_value
                    ),

                    Product.code.ilike(
                        search_value
                    ),

                    Product.brand.ilike(
                        search_value
                    ),

                    Product.description.ilike(
                        search_value
                    ),

                    variant_search_exists,
                )
            )


        # =================================================
        # AUDIENCIA
        # =================================================

        if (
            audience
            and
            audience.strip()
        ):

            normalized_audience = (
                audience.strip()
            )

            query = query.filter(
                Audience.name.ilike(
                    normalized_audience
                )
            )


        # =================================================
        # CATEGORÍA
        # =================================================

        if (
            category
            and
            category.strip()
        ):

            normalized_category = (
                category.strip()
            )

            query = query.filter(
                Category.name.ilike(
                    normalized_category
                )
            )


        # =================================================
        # TALLA
        # =================================================

        if (
            size_id
            is not None
        ):

            size_variant_exists = (
                db.query(
                    ProductVariant.id
                )
                .join(
                    Size,
                    ProductVariant.size_id
                    == Size.id,
                )
                .filter(
                    ProductVariant.product_id
                    == Product.id,

                    ProductVariant.is_active.is_(
                        True
                    ),

                    Size.is_active.is_(
                        True
                    ),

                    ProductVariant.size_id
                    == size_id,
                )
                .exists()
            )


            query = query.filter(
                size_variant_exists
            )


        # =================================================
        # COLOR
        # =================================================

        if (
            color_id
            is not None
        ):

            color_variant_exists = (
                db.query(
                    ProductVariant.id
                )
                .join(
                    Color,
                    ProductVariant.color_id
                    == Color.id,
                )
                .filter(
                    ProductVariant.product_id
                    == Product.id,

                    ProductVariant.is_active.is_(
                        True
                    ),

                    Color.is_active.is_(
                        True
                    ),

                    ProductVariant.color_id
                    == color_id,
                )
                .exists()
            )


            query = query.filter(
                color_variant_exists
            )


        # =================================================
        # PRECIO MÍNIMO
        # =================================================

        if (
            min_price
            is not None
        ):

            min_price_variant_exists = (
                db.query(
                    ProductVariant.id
                )
                .filter(
                    ProductVariant.product_id
                    == Product.id,

                    ProductVariant.is_active.is_(
                        True
                    ),

                    (
                        Product.base_price
                        +
                        func.coalesce(
                            ProductVariant.additional_price,
                            Decimal(
                                "0.00"
                            ),
                        )
                    )
                    >=
                    min_price,
                )
                .exists()
            )


            query = query.filter(
                min_price_variant_exists
            )


        # =================================================
        # PRECIO MÁXIMO
        # =================================================

        if (
            max_price
            is not None
        ):

            max_price_variant_exists = (
                db.query(
                    ProductVariant.id
                )
                .filter(
                    ProductVariant.product_id
                    == Product.id,

                    ProductVariant.is_active.is_(
                        True
                    ),

                    (
                        Product.base_price
                        +
                        func.coalesce(
                            ProductVariant.additional_price,
                            Decimal(
                                "0.00"
                            ),
                        )
                    )
                    <=
                    max_price,
                )
                .exists()
            )


            query = query.filter(
                max_price_variant_exists
            )


        # =================================================
        # PROMOCIÓN ACTIVA
        # =================================================

        if (
            promotion
            is True
        ):

            now = datetime.now(
                timezone.utc
            )


            promotion_exists = (
                db.query(
                    ProductPromotion.id
                )
                .join(
                    Promotion,
                    ProductPromotion.promotion_id
                    == Promotion.id,
                )
                .filter(
                    ProductPromotion.product_id
                    == Product.id,

                    Promotion.is_active.is_(
                        True
                    ),

                    Promotion.start_at
                    <=
                    now,

                    Promotion.end_at
                    >=
                    now,
                )
                .exists()
            )


            query = query.filter(
                promotion_exists
            )


        # =================================================
        # PROMOCIÓN ESPECÍFICA
        # =================================================

        if promotion_id is not None:

            now = datetime.now(timezone.utc)

            promotion_id_exists = (
                db.query(ProductPromotion.id)
                .join(
                    Promotion,
                    ProductPromotion.promotion_id == Promotion.id,
                )
                .filter(
                    ProductPromotion.product_id == Product.id,
                    ProductPromotion.promotion_id == promotion_id,
                    Promotion.is_active.is_(True),
                    Promotion.start_at <= now,
                    Promotion.end_at >= now,
                )
                .exists()
            )

            query = query.filter(promotion_id_exists)


        # =================================================
        # COLECCIÓN ESPECÍFICA
        # =================================================

        if collection_id is not None:

            today = datetime.now(timezone.utc).date()

            collection_exists = (
                db.query(ProductCollection.id)
                .join(
                    Collection,
                    ProductCollection.collection_id == Collection.id,
                )
                .filter(
                    ProductCollection.product_id == Product.id,
                    ProductCollection.collection_id == collection_id,
                    Collection.is_active.is_(True),
                    or_(
                        Collection.launch_date.is_(None),
                        Collection.launch_date <= today,
                    ),
                )
                .exists()
            )

            query = query.filter(collection_exists)


        # =================================================
        # TEMPORADA ESPECÍFICA
        # =================================================

        if season_id is not None:

            today = datetime.now(timezone.utc).date()

            season_exists = (
                db.query(ProductSeason.id)
                .join(
                    Season,
                    ProductSeason.season_id == Season.id,
                )
                .filter(
                    ProductSeason.product_id == Product.id,
                    ProductSeason.season_id == season_id,
                    Season.is_active.is_(True),
                    or_(Season.start_date.is_(None), Season.start_date <= today),
                    or_(Season.end_date.is_(None), Season.end_date >= today),
                )
                .exists()
            )

            query = query.filter(season_exists)


        # =================================================
        # STOCK DISPONIBLE
        # =================================================

        if (
            in_stock
            is not None
        ):

            stock_query = (
                db.query(
                    Inventory.id
                )
                .join(
                    ProductVariant,
                    Inventory.product_variant_id
                    == ProductVariant.id,
                )
                .join(
                    Branch,
                    Inventory.branch_id
                    == Branch.id,
                )
                .filter(
                    ProductVariant.product_id
                    == Product.id,

                    ProductVariant.is_active.is_(
                        True
                    ),

                    Inventory.is_active.is_(
                        True
                    ),

                    Branch.is_active.is_(
                        True
                    ),

                    (
                        Inventory.stock_quantity
                        -
                        Inventory.reserved_quantity
                    )
                    >
                    0,
                )
            )


            # =============================================
            # FILTRAR POR SUCURSAL SI FUE ENVIADA
            # =============================================

            if (
                branch_id
                is not None
            ):

                stock_query = (
                    stock_query.filter(
                        Inventory.branch_id
                        == branch_id
                    )
                )


            stock_exists = (
                stock_query.exists()
            )


            if (
                in_stock
                is True
            ):

                query = query.filter(
                    stock_exists
                )

            else:

                query = query.filter(
                    ~stock_exists
                )


        # =================================================
        # TOTAL
        # =================================================

        total = (
            query
            .distinct(
                Product.id
            )
            .count()
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
        # ORDEN
        # =================================================

        sort_columns = {

            "name":
                Product.name,

            "price":
                Product.base_price,

            "created_at":
                Product.created_at,
        }


        sort_column = (
            sort_columns.get(
                sort_by,
                Product.name,
            )
        )


        if (
            sort_order
            == "desc"
        ):

            query = query.order_by(
                sort_column.desc(),
                Product.id.desc(),
            )

        else:

            query = query.order_by(
                sort_column.asc(),
                Product.id.asc(),
            )


        # =================================================
        # PAGINACIÓN
        # =================================================

        products = (
            query
            .distinct()
            .offset(
                (
                    page - 1
                )
                *
                page_size
            )
            .limit(
                page_size
            )
            .all()
        )


        # =================================================
        # SIN RESULTADOS
        # =================================================

        if (
            not products
        ):

            return {

                "items":
                    [],

                "page":
                    page,

                "page_size":
                    page_size,

                "total":
                    total,

                "total_pages":
                    total_pages,
            }


        product_ids = [

            product.id

            for product
            in products
        ]


        # =================================================
        # PROMOCIONES ACTIVAS POR PRODUCTO
        # =================================================

        promotions_by_product = (
            CustomerPricingService.get_active_promotions_by_product(
                db,
                product_ids,
            )
        )


        # =================================================
        # VARIANTES ACTIVAS
        # =================================================

        variants = (
            db.query(
                ProductVariant
            )
            .filter(
                ProductVariant.product_id.in_(
                    product_ids
                ),

                ProductVariant.is_active.is_(
                    True
                ),
            )
            .all()
        )


        variants_by_product: dict[
            int,
            list[
                ProductVariant
            ],
        ] = {}


        for variant in variants:

            variants_by_product.setdefault(
                variant.product_id,
                [],
            ).append(
                variant
            )


        variant_ids = [

            variant.id

            for variant
            in variants
        ]


        # =================================================
        # DISPONIBILIDAD POR VARIANTE
        # =================================================

        available_by_variant: dict[
            int,
            int,
        ] = {}


        if (
            variant_ids
        ):

            availability_query = (
                db.query(
                    Inventory.product_variant_id,

                    func.coalesce(
                        func.sum(
                            Inventory.stock_quantity
                            -
                            Inventory.reserved_quantity
                        ),
                        0,
                    ).label(
                        "total_available"
                    ),
                )
                .join(
                    Branch,
                    Inventory.branch_id
                    == Branch.id,
                )
                .filter(
                    Inventory.product_variant_id.in_(
                        variant_ids
                    ),

                    Inventory.is_active.is_(
                        True
                    ),

                    Branch.is_active.is_(
                        True
                    ),
                )
            )


            # =============================================
            # FILTRAR DISPONIBILIDAD POR SUCURSAL
            # =============================================

            if (
                branch_id
                is not None
            ):

                availability_query = (
                    availability_query.filter(
                        Inventory.branch_id
                        == branch_id
                    )
                )


            availability_rows = (
                availability_query
                .group_by(
                    Inventory.product_variant_id
                )
                .all()
            )


            available_by_variant = {

                row.product_variant_id:
                    int(
                        row.total_available
                        or 0
                    )

                for row
                in availability_rows
            }


        # =================================================
        # ARMAR RESPUESTA
        # =================================================

        items = []


        for product in products:

            product_variants = (
                variants_by_product.get(
                    product.id,
                    [],
                )
            )


            # =============================================
            # PRECIOS
            # =============================================

            variant_prices = [

                (
                    product.base_price
                    +
                    (
                        variant.additional_price
                        or Decimal(
                            "0.00"
                        )
                    )
                )

                for variant
                in product_variants
            ]


            if (
                variant_prices
            ):

                calculated_min_price = min(
                    variant_prices
                )

                calculated_max_price = max(
                    variant_prices
                )

            else:

                calculated_min_price = (
                    product.base_price
                )

                calculated_max_price = (
                    product.base_price
                )


            original_min_price = calculated_min_price
            original_max_price = calculated_max_price

            applied_promotion = (
                CustomerPricingService.choose_best_promotion(
                    promotions_by_product.get(product.id),
                    original_min_price,
                )
            )

            if applied_promotion is not None:
                calculated_min_price = CustomerPricingService.apply_discount(
                    original_min_price,
                    applied_promotion,
                )
                calculated_max_price = CustomerPricingService.apply_discount(
                    original_max_price,
                    applied_promotion,
                )


            # =============================================
            # STOCK
            # =============================================

            total_available = sum(

                available_by_variant.get(
                    variant.id,
                    0,
                )

                for variant
                in product_variants
            )


            available_variants = sum(

                1

                for variant
                in product_variants

                if (
                    available_by_variant.get(
                        variant.id,
                        0,
                    )
                    >
                    0
                )
            )


            # =============================================
            # ITEM
            # =============================================

            items.append(
                {

                    "id":
                        product.id,

                    "code":
                        product.code,

                    "name":
                        product.name,

                    "description":
                        product.description,

                    "brand":
                        product.brand,

                    "base_price":
                        product.base_price,

                    "min_price":
                        calculated_min_price,

                    "max_price":
                        calculated_max_price,

                    "original_min_price":
                        original_min_price,

                    "original_max_price":
                        original_max_price,

                    "has_discount":
                        applied_promotion is not None
                        and calculated_min_price < original_min_price,

                    "promotion":
                        CustomerPricingService.promotion_payload(applied_promotion),

                    "cover_image_url":
                        product.cover_image_url,

                    "category_id":
                        product.category_id,

                    "audience_id":
                        product.audience_id,

                    "category":
                        product.category,

                    "audience":
                        product.audience,

                    "variant_count":
                        len(
                            product_variants
                        ),

                    "available_variants":
                        available_variants,

                    "total_available":
                        total_available,

                    "has_stock":
                        (
                            total_available
                            >
                            0
                        ),
                }
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