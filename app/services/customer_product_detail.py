from decimal import Decimal

from fastapi import (
    HTTPException,
    status,
)

from sqlalchemy import (
    func,
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

from app.models.city import (
    City,
)

from app.models.color import (
    Color,
)

from app.models.inventory import (
    Inventory,
)

from app.models.product import (
    Product,
)

from app.models.product_image import (
    ProductImage,
)

from app.models.product_variant import (
    ProductVariant,
)

from app.models.size import (
    Size,
)


class CustomerProductDetailService:

    # =====================================================
    # CU26 - CONSULTAR DETALLE DE PRENDA
    # =====================================================

    @staticmethod
    def get_product_detail(
        db: Session,

        product_id: int,

        branch_id: int | None = None,
    ) -> dict:

        # =================================================
        # PRODUCTO
        # =================================================

        product = (
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
                Product.id
                == product_id,

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
            .first()
        )


        if (
            product is None
        ):

            raise HTTPException(
                status_code=
                    status.HTTP_404_NOT_FOUND,

                detail=
                    "La prenda no existe o no está disponible.",
            )


        # =================================================
        # IMÁGENES ACTIVAS
        # =================================================

        images = (
            db.query(
                ProductImage
            )
            .filter(
                ProductImage.product_id
                == product.id,

                ProductImage.is_active.is_(
                    True
                ),
            )
            .order_by(
                ProductImage.is_primary.desc(),

                ProductImage.sort_order.asc(),

                ProductImage.id.asc(),
            )
            .all()
        )


        # =================================================
        # VARIANTES ACTIVAS
        # =================================================

        variants = (
            db.query(
                ProductVariant
            )
            .join(
                Size,
                ProductVariant.size_id
                == Size.id,
            )
            .join(
                Color,
                ProductVariant.color_id
                == Color.id,
            )
            .options(
                joinedload(
                    ProductVariant.size
                ),

                joinedload(
                    ProductVariant.color
                ),
            )
            .filter(
                ProductVariant.product_id
                == product.id,

                ProductVariant.is_active.is_(
                    True
                ),

                Size.is_active.is_(
                    True
                ),

                Color.is_active.is_(
                    True
                ),
            )
            .order_by(
                Size.sort_order.asc(),

                Size.name.asc(),

                Color.name.asc(),

                ProductVariant.id.asc(),
            )
            .all()
        )


        # =================================================
        # IDS DE VARIANTES
        # =================================================

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
            # FILTRAR POR SUCURSAL SI FUE ENVIADA
            # =============================================

            if (
                branch_id
                is not None
            ):

                availability_query = (
                    availability_query
                    .filter(
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
                    max(
                        0,
                        int(
                            row.total_available
                            or 0
                        ),
                    )

                for row
                in availability_rows
            }


        # =================================================
        # ARMAR VARIANTES
        # =================================================

        variant_items = []


        variant_prices: list[
            Decimal
        ] = []


        total_available = 0

        available_variants = 0


        for variant in variants:

            additional_price = (
                variant.additional_price
                or Decimal(
                    "0.00"
                )
            )


            final_price = (
                product.base_price
                +
                additional_price
            )


            variant_prices.append(
                final_price
            )


            variant_available = (
                available_by_variant.get(
                    variant.id,
                    0,
                )
            )


            total_available += (
                variant_available
            )


            if (
                variant_available
                >
                0
            ):

                available_variants += 1


            variant_items.append(
                {

                    "id":
                        variant.id,

                    "sku":
                        variant.sku,

                    "size_id":
                        variant.size_id,

                    "color_id":
                        variant.color_id,

                    "additional_price":
                        additional_price,

                    "final_price":
                        final_price,

                    "image_url":
                        variant.image_url,

                    "size":
                        variant.size,

                    "color":
                        variant.color,

                    "total_available":
                        variant_available,

                    "has_stock":
                        (
                            variant_available
                            >
                            0
                        ),
                }
            )


        # =================================================
        # PRECIOS
        # =================================================

        if (
            variant_prices
        ):

            min_price = min(
                variant_prices
            )

            max_price = max(
                variant_prices
            )

        else:

            min_price = (
                product.base_price
            )

            max_price = (
                product.base_price
            )


        # =================================================
        # RESPUESTA
        # =================================================

        return {

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
                min_price,

            "max_price":
                max_price,

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

            "images":
                images,

            "variants":
                variant_items,

            "variant_count":
                len(
                    variants
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


    # =====================================================
    # CU26 - CONSULTAR DISPONIBILIDAD EN SUCURSALES
    # =====================================================

    @staticmethod
    def get_variant_availability(
        db: Session,

        product_id: int,

        variant_id: int,

        city_id: int | None = None,
    ) -> dict:

        # =================================================
        # VALIDAR PRODUCTO
        # =================================================

        product = (
            db.query(
                Product
            )
            .filter(
                Product.id
                == product_id,

                Product.is_active.is_(
                    True
                ),
            )
            .first()
        )


        if (
            product is None
        ):

            raise HTTPException(
                status_code=
                    status.HTTP_404_NOT_FOUND,

                detail=
                    "La prenda no existe o no está disponible.",
            )


        # =================================================
        # VALIDAR VARIANTE
        # =================================================

        variant = (
            db.query(
                ProductVariant
            )
            .join(
                Size,
                ProductVariant.size_id
                == Size.id,
            )
            .join(
                Color,
                ProductVariant.color_id
                == Color.id,
            )
            .options(
                joinedload(
                    ProductVariant.size
                ),

                joinedload(
                    ProductVariant.color
                ),
            )
            .filter(
                ProductVariant.id
                == variant_id,

                ProductVariant.product_id
                == product_id,

                ProductVariant.is_active.is_(
                    True
                ),

                Size.is_active.is_(
                    True
                ),

                Color.is_active.is_(
                    True
                ),
            )
            .first()
        )


        if (
            variant is None
        ):

            raise HTTPException(
                status_code=
                    status.HTTP_404_NOT_FOUND,

                detail=
                    "La variante solicitada no existe o no pertenece a esta prenda.",
            )


        # =================================================
        # VALIDAR CIUDAD SI FUE ENVIADA
        # =================================================

        if (
            city_id
            is not None
        ):

            city = (
                db.query(
                    City
                )
                .filter(
                    City.id
                    == city_id,

                    City.is_active.is_(
                        True
                    ),
                )
                .first()
            )


            if (
                city is None
            ):

                raise HTTPException(
                    status_code=
                        status.HTTP_404_NOT_FOUND,

                    detail=
                        "La ciudad solicitada no existe o no está disponible.",
                )


        # =================================================
        # CONSULTA BASE DE DISPONIBILIDAD
        # =================================================

        availability_query = (
            db.query(
                Branch.id.label(
                    "branch_id"
                ),

                Branch.name.label(
                    "branch_name"
                ),

                Branch.address.label(
                    "address"
                ),

                Branch.phone.label(
                    "phone"
                ),

                City.id.label(
                    "city_id"
                ),

                City.name.label(
                    "city_name"
                ),

                func.coalesce(
                    func.sum(
                        Inventory.stock_quantity
                        -
                        Inventory.reserved_quantity
                    ),
                    0,
                ).label(
                    "available_quantity"
                ),
            )
            .join(
                Inventory,
                Inventory.branch_id
                == Branch.id,
            )
            .join(
                City,
                Branch.city_id
                == City.id,
            )
            .filter(
                Inventory.product_variant_id
                == variant.id,

                Inventory.is_active.is_(
                    True
                ),

                Branch.is_active.is_(
                    True
                ),

                City.is_active.is_(
                    True
                ),
            )
        )


        # =================================================
        # FILTRAR POR CIUDAD
        # =================================================

        if (
            city_id
            is not None
        ):

            availability_query = (
                availability_query
                .filter(
                    City.id
                    == city_id
                )
            )


        # =================================================
        # AGRUPAR POR SUCURSAL
        # =================================================

        availability_rows = (
            availability_query
            .group_by(
                Branch.id,

                Branch.name,

                Branch.address,

                Branch.phone,

                City.id,

                City.name,
            )
            .all()
        )


        # =================================================
        # ARMAR SUCURSALES
        # SOLO DEVOLVER CON STOCK REAL
        # =================================================

        branches = []


        for row in availability_rows:

            available_quantity = max(
                0,

                int(
                    row.available_quantity
                    or 0
                ),
            )


            if (
                available_quantity
                <= 0
            ):
                continue


            branches.append(
                {

                    "branch_id":
                        row.branch_id,

                    "branch_name":
                        row.branch_name,

                    "city_id":
                        row.city_id,

                    "city_name":
                        row.city_name,

                    "address":
                        row.address,

                    "phone":
                        row.phone,

                    "available_quantity":
                        available_quantity,

                    "has_stock":
                        True,
                }
            )


        # =================================================
        # ORDENAR SUCURSALES
        # =================================================

        branches.sort(
            key=lambda item: (
                item["branch_name"].lower(),
            )
        )


        # =================================================
        # TOTAL DISPONIBLE
        # =================================================

        total_available = sum(

            branch[
                "available_quantity"
            ]

            for branch
            in branches
        )


        # =================================================
        # RESPUESTA
        # =================================================

        return {

            "product_id":
                product.id,

            "product_name":
                product.name,

            "variant_id":
                variant.id,

            "sku":
                variant.sku,

            "size":
                variant.size,

            "color":
                variant.color,

            "total_available":
                total_available,

            "available_branches":
                len(
                    branches
                ),

            "branches":
                branches,
        }