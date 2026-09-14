import math

from decimal import Decimal
from typing import Literal

from sqlalchemy import (
    func,
    or_,
)

from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.audience import Audience
from app.models.category import Category
from app.models.product import Product

from app.schemas.product import (
    ProductCreate,
    ProductUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class ProductService:

    # =====================================================
    # QUERY BASE
    # =====================================================

    @staticmethod
    def _base_query(
        db: Session,
    ):

        return (
            db.query(Product)
            .options(
                joinedload(
                    Product.category
                ),
                joinedload(
                    Product.audience
                ),
            )
        )


    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_products(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        category_id: int | None = None,
        audience_id: int | None = None,
        brand: str | None = None,
        is_active: bool | None = None,
        price_from: Decimal | None = None,
        price_to: Decimal | None = None,
        sort_by: Literal[
            "id",
            "code",
            "name",
            "brand",
            "base_price",
            "is_active",
            "created_at",
            "updated_at",
        ] = "name",
        sort_order: Literal[
            "asc",
            "desc",
        ] = "asc",
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
            ProductService
            ._base_query(db)
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
                        Product.code.ilike(
                            pattern
                        ),
                        Product.name.ilike(
                            pattern
                        ),
                        Product.description.ilike(
                            pattern
                        ),
                        Product.brand.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # CATEGORÍA
        # =================================================

        if category_id is not None:

            query = query.filter(
                Product.category_id
                == category_id
            )

        # =================================================
        # AUDIENCIA
        # =================================================

        if audience_id is not None:

            query = query.filter(
                Product.audience_id
                == audience_id
            )

        # =================================================
        # MARCA
        # =================================================

        if brand:

            clean_brand = (
                brand.strip()
            )

            if clean_brand:

                query = query.filter(
                    Product.brand.ilike(
                        f"%{clean_brand}%"
                    )
                )

        # =================================================
        # ESTADO
        # =================================================

        if is_active is not None:

            query = query.filter(
                Product.is_active
                == is_active
            )

        # =================================================
        # PRECIO DESDE
        # =================================================

        if price_from is not None:

            query = query.filter(
                Product.base_price
                >= price_from
            )

        # =================================================
        # PRECIO HASTA
        # =================================================

        if price_to is not None:

            query = query.filter(
                Product.base_price
                <= price_to
            )

        total = query.count()

        # =================================================
        # ORDENAMIENTO
        # =================================================

        sort_columns = {
            "id":
                Product.id,

            "code":
                Product.code,

            "name":
                Product.name,

            "brand":
                Product.brand,

            "base_price":
                Product.base_price,

            "is_active":
                Product.is_active,

            "created_at":
                Product.created_at,

            "updated_at":
                Product.updated_at,
        }

        sort_column = (
            sort_columns[
                sort_by
            ]
        )

        if sort_order == "desc":

            query = query.order_by(
                sort_column.desc(),
                Product.id.desc(),
            )

        else:

            query = query.order_by(
                sort_column.asc(),
                Product.id.asc(),
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
                total / page_size
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
    def get_product(
        db: Session,
        product_id: int,
    ) -> Product:

        product = (
            ProductService
            ._base_query(db)
            .filter(
                Product.id
                == product_id
            )
            .first()
        )

        if product is None:

            raise LookupError(
                "Producto no encontrado."
            )

        return product


    # =====================================================
    # VALIDAR CÓDIGO ÚNICO
    # =====================================================

    @staticmethod
    def _validate_unique_code(
        db: Session,
        code: str,
        exclude_id: int | None = None,
    ) -> None:

        clean_code = (
            code.strip()
        )

        query = (
            db.query(Product)
            .filter(
                func.lower(
                    Product.code
                )
                ==
                clean_code.lower()
            )
        )

        if exclude_id is not None:

            query = query.filter(
                Product.id
                != exclude_id
            )

        if query.first() is not None:

            raise ValueError(
                "Ya existe un producto "
                "con ese código."
            )


    # =====================================================
    # VALIDAR CATEGORÍA
    # =====================================================

    @staticmethod
    def _validate_category(
        db: Session,
        category_id: int,
    ) -> Category:

        category = db.get(
            Category,
            category_id,
        )

        if category is None:

            raise ValueError(
                "La categoría seleccionada "
                "no existe."
            )

        if not category.is_active:

            raise ValueError(
                "La categoría seleccionada "
                "está inactiva."
            )

        return category


    # =====================================================
    # VALIDAR AUDIENCIA
    # =====================================================

    @staticmethod
    def _validate_audience(
        db: Session,
        audience_id: int,
    ) -> Audience:

        audience = db.get(
            Audience,
            audience_id,
        )

        if audience is None:

            raise ValueError(
                "La audiencia seleccionada "
                "no existe."
            )

        if not audience.is_active:

            raise ValueError(
                "La audiencia seleccionada "
                "está inactiva."
            )

        return audience


    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_product(
        db: Session,
        payload: ProductCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Product:

        clean_code = (
            payload.code
            .strip()
            .upper()
        )

        clean_name = (
            payload.name
            .strip()
        )

        clean_description = (
            payload.description.strip()
            if payload.description
            else None
        )

        clean_brand = (
            payload.brand.strip()
            if payload.brand
            else None
        )

        ProductService._validate_unique_code(
            db=db,
            code=clean_code,
        )

        ProductService._validate_category(
            db=db,
            category_id=
                payload.category_id,
        )

        ProductService._validate_audience(
            db=db,
            audience_id=
                payload.audience_id,
        )

        product = Product(
            code=
                clean_code,

            name=
                clean_name,

            description=
                clean_description,

            brand=
                clean_brand,

            base_price=
                payload.base_price,

            category_id=
                payload.category_id,

            audience_id=
                payload.audience_id,

            cover_image_url=
                None,

            cover_image_public_id=
                None,

            is_active=
                True,
        )

        db.add(
            product
        )

        db.flush()

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "CREATE_PRODUCT",

            module=
                "CATALOG",

            entity_type=
                "Product",

            entity_id=
                product.id,

            description=(
                f"Se creó el producto "
                f"'{product.name}'."
            ),

            old_values=
                None,

            new_values={
                "code":
                    product.code,

                "name":
                    product.name,

                "description":
                    product.description,

                "brand":
                    product.brand,

                "base_price":
                    str(
                        product.base_price
                    ),

                "category_id":
                    product.category_id,

                "audience_id":
                    product.audience_id,

                "is_active":
                    product.is_active,
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
            ProductService
            .get_product(
                db=db,
                product_id=
                    product.id,
            )
        )


    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_product(
        db: Session,
        product_id: int,
        payload: ProductUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Product:

        product = (
            ProductService
            .get_product(
                db=db,
                product_id=
                    product_id,
            )
        )

        old_values = {
            "code":
                product.code,

            "name":
                product.name,

            "description":
                product.description,

            "brand":
                product.brand,

            "base_price":
                str(
                    product.base_price
                ),

            "category_id":
                product.category_id,

            "audience_id":
                product.audience_id,

            "is_active":
                product.is_active,
        }

        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )

        # =================================================
        # CODE
        # =================================================

        if (
            "code" in update_data
            and update_data[
                "code"
            ] is not None
        ):

            clean_code = (
                update_data[
                    "code"
                ]
                .strip()
                .upper()
            )

            ProductService._validate_unique_code(
                db=db,
                code=clean_code,
                exclude_id=
                    product.id,
            )

            product.code = (
                clean_code
            )

        # =================================================
        # NAME
        # =================================================

        if (
            "name" in update_data
            and update_data[
                "name"
            ] is not None
        ):

            product.name = (
                update_data[
                    "name"
                ].strip()
            )

        # =================================================
        # DESCRIPTION
        # =================================================

        if (
            "description"
            in update_data
        ):

            description = (
                update_data[
                    "description"
                ]
            )

            product.description = (
                description.strip()
                if description
                else None
            )

        # =================================================
        # BRAND
        # =================================================

        if (
            "brand"
            in update_data
        ):

            brand = (
                update_data[
                    "brand"
                ]
            )

            product.brand = (
                brand.strip()
                if brand
                else None
            )

        # =================================================
        # PRICE
        # =================================================

        if (
            "base_price"
            in update_data
            and update_data[
                "base_price"
            ] is not None
        ):

            product.base_price = (
                update_data[
                    "base_price"
                ]
            )

        # =================================================
        # CATEGORY
        # =================================================

        if (
            "category_id"
            in update_data
            and update_data[
                "category_id"
            ] is not None
        ):

            ProductService._validate_category(
                db=db,
                category_id=
                    update_data[
                        "category_id"
                    ],
            )

            product.category_id = (
                update_data[
                    "category_id"
                ]
            )

        # =================================================
        # AUDIENCE
        # =================================================

        if (
            "audience_id"
            in update_data
            and update_data[
                "audience_id"
            ] is not None
        ):

            ProductService._validate_audience(
                db=db,
                audience_id=
                    update_data[
                        "audience_id"
                    ],
            )

            product.audience_id = (
                update_data[
                    "audience_id"
                ]
            )

        # =================================================
        # ACTIVE
        # =================================================

        if (
            "is_active"
            in update_data
            and update_data[
                "is_active"
            ] is not None
        ):

            product.is_active = (
                update_data[
                    "is_active"
                ]
            )

        db.flush()

        new_values = {
            "code":
                product.code,

            "name":
                product.name,

            "description":
                product.description,

            "brand":
                product.brand,

            "base_price":
                str(
                    product.base_price
                ),

            "category_id":
                product.category_id,

            "audience_id":
                product.audience_id,

            "is_active":
                product.is_active,
        }

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_PRODUCT",

            module=
                "CATALOG",

            entity_type=
                "Product",

            entity_id=
                product.id,

            description=(
                f"Se actualizó el producto "
                f"'{product.name}'."
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
            ProductService
            .get_product(
                db=db,
                product_id=
                    product.id,
            )
        )


    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_product(
        db: Session,
        product_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Product:

        product = (
            ProductService
            .get_product(
                db=db,
                product_id=
                    product_id,
            )
        )

        if not product.is_active:

            raise ValueError(
                "El producto ya se encuentra "
                "inactivo."
            )

        product.is_active = False

        db.flush()

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "DEACTIVATE_PRODUCT",

            module=
                "CATALOG",

            entity_type=
                "Product",

            entity_id=
                product.id,

            description=(
                f"Se desactivó el producto "
                f"'{product.name}'."
            ),

            old_values={
                "is_active":
                    True,
            },

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
            ProductService
            .get_product(
                db=db,
                product_id=
                    product.id,
            )
        )


    # =====================================================
    # ACTUALIZAR PORTADA
    # =====================================================

    @staticmethod
    def update_cover(
        db: Session,
        product_id: int,
        image_url: str,
        public_id: str,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Product:

        product = (
            ProductService
            .get_product(
                db=db,
                product_id=
                    product_id,
            )
        )

        old_values = {
            "cover_image_url":
                product.cover_image_url,

            "cover_image_public_id":
                product.cover_image_public_id,
        }

        product.cover_image_url = (
            image_url
        )

        product.cover_image_public_id = (
            public_id
        )

        db.flush()

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_PRODUCT_COVER",

            module=
                "CATALOG",

            entity_type=
                "Product",

            entity_id=
                product.id,

            description=(
                f"Se actualizó la portada "
                f"del producto '{product.name}'."
            ),

            old_values=
                old_values,

            new_values={
                "cover_image_url":
                    product.cover_image_url,

                "cover_image_public_id":
                    product.cover_image_public_id,
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
            ProductService
            .get_product(
                db=db,
                product_id=
                    product.id,
            )
        )


    # =====================================================
    # ELIMINAR PORTADA DE BD
    # =====================================================

    @staticmethod
    def remove_cover(
        db: Session,
        product_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Product:

        product = (
            ProductService
            .get_product(
                db=db,
                product_id=
                    product_id,
            )
        )

        if (
            product.cover_image_url is None
            and
            product.cover_image_public_id is None
        ):

            raise ValueError(
                "El producto no tiene "
                "una portada registrada."
            )

        old_values = {
            "cover_image_url":
                product.cover_image_url,

            "cover_image_public_id":
                product.cover_image_public_id,
        }

        product.cover_image_url = None
        product.cover_image_public_id = None

        db.flush()

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "REMOVE_PRODUCT_COVER",

            module=
                "CATALOG",

            entity_type=
                "Product",

            entity_id=
                product.id,

            description=(
                f"Se eliminó la portada "
                f"del producto '{product.name}'."
            ),

            old_values=
                old_values,

            new_values={
                "cover_image_url":
                    None,

                "cover_image_public_id":
                    None,
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
            ProductService
            .get_product(
                db=db,
                product_id=
                    product.id,
            )
        )