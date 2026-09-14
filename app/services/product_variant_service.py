from sqlalchemy import func
from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.color import Color
from app.models.product import Product
from app.models.product_variant import (
    ProductVariant,
)
from app.models.size import Size

from app.schemas.product_variant import (
    ProductVariantCreate,
    ProductVariantUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class ProductVariantService:

    # =====================================================
    # QUERY BASE
    # =====================================================

    @staticmethod
    def _base_query(
        db: Session,
    ):

        return (
            db.query(ProductVariant)
            .options(
                joinedload(
                    ProductVariant.size
                ),
                joinedload(
                    ProductVariant.color
                ),
            )
        )


    # =====================================================
    # PRODUCTO
    # =====================================================

    @staticmethod
    def _validate_product(
        db: Session,
        product_id: int,
    ) -> Product:

        product = db.get(
            Product,
            product_id,
        )

        if product is None:
            raise LookupError(
                "Producto no encontrado."
            )

        return product


    # =====================================================
    # TALLA
    # =====================================================

    @staticmethod
    def _validate_size(
        db: Session,
        size_id: int,
    ) -> Size:

        size = db.get(
            Size,
            size_id,
        )

        if size is None:
            raise ValueError(
                "La talla seleccionada "
                "no existe."
            )

        if not size.is_active:
            raise ValueError(
                "La talla seleccionada "
                "está inactiva."
            )

        return size


    # =====================================================
    # COLOR
    # =====================================================

    @staticmethod
    def _validate_color(
        db: Session,
        color_id: int,
    ) -> Color:

        color = db.get(
            Color,
            color_id,
        )

        if color is None:
            raise ValueError(
                "El color seleccionado "
                "no existe."
            )

        if not color.is_active:
            raise ValueError(
                "El color seleccionado "
                "está inactivo."
            )

        return color


    # =====================================================
    # SKU ÚNICO
    # =====================================================

    @staticmethod
    def _validate_unique_sku(
        db: Session,
        sku: str,
        exclude_id: int | None = None,
    ) -> None:

        clean_sku = (
            sku.strip().upper()
        )

        query = (
            db.query(ProductVariant)
            .filter(
                func.lower(
                    ProductVariant.sku
                )
                ==
                clean_sku.lower()
            )
        )

        if exclude_id is not None:
            query = query.filter(
                ProductVariant.id
                != exclude_id
            )

        if query.first():
            raise ValueError(
                "Ya existe una variante "
                "con ese SKU."
            )


    # =====================================================
    # COMBINACIÓN ÚNICA
    # =====================================================

    @staticmethod
    def _validate_combination(
        db: Session,
        product_id: int,
        size_id: int,
        color_id: int,
        exclude_id: int | None = None,
    ) -> None:

        query = (
            db.query(ProductVariant)
            .filter(
                ProductVariant.product_id
                == product_id,
                ProductVariant.size_id
                == size_id,
                ProductVariant.color_id
                == color_id,
            )
        )

        if exclude_id is not None:
            query = query.filter(
                ProductVariant.id
                != exclude_id
            )

        if query.first():
            raise ValueError(
                "Ya existe una variante "
                "con esa talla y color "
                "para este producto."
            )


    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_variants(
        db: Session,
        product_id: int,
        include_inactive: bool = False,
    ) -> list[ProductVariant]:

        ProductVariantService._validate_product(
            db=db,
            product_id=product_id,
        )

        query = (
            ProductVariantService
            ._base_query(db)
            .filter(
                ProductVariant.product_id
                == product_id
            )
        )

        if not include_inactive:
            query = query.filter(
                ProductVariant.is_active
                == True
            )

        return (
            query
            .order_by(
                ProductVariant.id.asc()
            )
            .all()
        )


    # =====================================================
    # OBTENER
    # =====================================================

    @staticmethod
    def get_variant(
        db: Session,
        variant_id: int,
    ) -> ProductVariant:

        variant = (
            ProductVariantService
            ._base_query(db)
            .filter(
                ProductVariant.id
                == variant_id
            )
            .first()
        )

        if variant is None:
            raise LookupError(
                "Variante no encontrada."
            )

        return variant


    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_variant(
        db: Session,
        product_id: int,
        payload: ProductVariantCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProductVariant:

        product = (
            ProductVariantService
            ._validate_product(
                db=db,
                product_id=product_id,
            )
        )

        ProductVariantService._validate_size(
            db=db,
            size_id=payload.size_id,
        )

        ProductVariantService._validate_color(
            db=db,
            color_id=payload.color_id,
        )

        clean_sku = (
            payload.sku
            .strip()
            .upper()
        )

        ProductVariantService._validate_unique_sku(
            db=db,
            sku=clean_sku,
        )

        ProductVariantService._validate_combination(
            db=db,
            product_id=product_id,
            size_id=payload.size_id,
            color_id=payload.color_id,
        )

        variant = ProductVariant(
            product_id=product_id,
            size_id=payload.size_id,
            color_id=payload.color_id,
            sku=clean_sku,
            additional_price=
                payload.additional_price,
            image_url=None,
            cloudinary_public_id=None,
            is_active=True,
        )

        db.add(variant)

        db.flush()

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="CREATE_PRODUCT_VARIANT",
            module="CATALOG",
            entity_type="ProductVariant",
            entity_id=variant.id,
            description=(
                f"Se creó una variante del "
                f"producto '{product.name}'."
            ),
            old_values=None,
            new_values={
                "product_id":
                    variant.product_id,
                "size_id":
                    variant.size_id,
                "color_id":
                    variant.color_id,
                "sku":
                    variant.sku,
                "additional_price":
                    str(
                        variant.additional_price
                    ),
                "is_active":
                    variant.is_active,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        return (
            ProductVariantService
            .get_variant(
                db=db,
                variant_id=variant.id,
            )
        )


    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_variant(
        db: Session,
        variant_id: int,
        payload: ProductVariantUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProductVariant:

        variant = (
            ProductVariantService
            .get_variant(
                db=db,
                variant_id=variant_id,
            )
        )

        old_values = {
            "size_id":
                variant.size_id,
            "color_id":
                variant.color_id,
            "sku":
                variant.sku,
            "additional_price":
                str(
                    variant.additional_price
                ),
            "is_active":
                variant.is_active,
        }

        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )

        new_size_id = (
            update_data.get(
                "size_id",
                variant.size_id,
            )
        )

        new_color_id = (
            update_data.get(
                "color_id",
                variant.color_id,
            )
        )

        ProductVariantService._validate_size(
            db=db,
            size_id=new_size_id,
        )

        ProductVariantService._validate_color(
            db=db,
            color_id=new_color_id,
        )

        ProductVariantService._validate_combination(
            db=db,
            product_id=variant.product_id,
            size_id=new_size_id,
            color_id=new_color_id,
            exclude_id=variant.id,
        )

        variant.size_id = new_size_id
        variant.color_id = new_color_id

        if (
            "sku" in update_data
            and update_data[
                "sku"
            ] is not None
        ):
            clean_sku = (
                update_data["sku"]
                .strip()
                .upper()
            )

            ProductVariantService._validate_unique_sku(
                db=db,
                sku=clean_sku,
                exclude_id=variant.id,
            )

            variant.sku = clean_sku

        if (
            "additional_price"
            in update_data
            and update_data[
                "additional_price"
            ] is not None
        ):
            variant.additional_price = (
                update_data[
                    "additional_price"
                ]
            )

        if (
            "is_active"
            in update_data
            and update_data[
                "is_active"
            ] is not None
        ):
            variant.is_active = (
                update_data[
                    "is_active"
                ]
            )

        db.flush()

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="UPDATE_PRODUCT_VARIANT",
            module="CATALOG",
            entity_type="ProductVariant",
            entity_id=variant.id,
            description=(
                "Se actualizó una variante "
                "del producto."
            ),
            old_values=old_values,
            new_values={
                "size_id":
                    variant.size_id,
                "color_id":
                    variant.color_id,
                "sku":
                    variant.sku,
                "additional_price":
                    str(
                        variant.additional_price
                    ),
                "is_active":
                    variant.is_active,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        return (
            ProductVariantService
            .get_variant(
                db=db,
                variant_id=variant.id,
            )
        )


    # =====================================================
    # IMAGEN
    # =====================================================

    @staticmethod
    def update_image(
        db: Session,
        variant_id: int,
        image_url: str,
        cloudinary_public_id: str,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProductVariant:

        variant = (
            ProductVariantService
            .get_variant(
                db=db,
                variant_id=variant_id,
            )
        )

        old_values = {
            "image_url":
                variant.image_url,
            "cloudinary_public_id":
                variant.cloudinary_public_id,
        }

        variant.image_url = image_url
        variant.cloudinary_public_id = (
            cloudinary_public_id
        )

        db.flush()

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="UPDATE_VARIANT_IMAGE",
            module="CATALOG",
            entity_type="ProductVariant",
            entity_id=variant.id,
            description=(
                "Se actualizó la imagen "
                "de una variante."
            ),
            old_values=old_values,
            new_values={
                "image_url":
                    variant.image_url,
                "cloudinary_public_id":
                    variant.cloudinary_public_id,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        return (
            ProductVariantService
            .get_variant(
                db=db,
                variant_id=variant.id,
            )
        )