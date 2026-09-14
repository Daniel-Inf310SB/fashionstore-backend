from sqlalchemy.orm import Session

from app.models.product import Product
from app.models.product_image import ProductImage

from app.schemas.product_image import (
    ProductImageUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class ProductImageService:

    # =====================================================
    # VALIDAR PRODUCTO
    # =====================================================

    @staticmethod
    def _get_product(
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
    # LISTAR
    # =====================================================

    @staticmethod
    def get_images(
        db: Session,
        product_id: int,
        include_inactive: bool = False,
    ) -> list[ProductImage]:

        ProductImageService._get_product(
            db=db,
            product_id=product_id,
        )

        query = (
            db.query(ProductImage)
            .filter(
                ProductImage.product_id
                == product_id
            )
        )

        if not include_inactive:
            query = query.filter(
                ProductImage.is_active
                == True
            )

        return (
            query
            .order_by(
                ProductImage.is_primary.desc(),
                ProductImage.sort_order.asc(),
                ProductImage.id.asc(),
            )
            .all()
        )


    # =====================================================
    # OBTENER
    # =====================================================

    @staticmethod
    def get_image(
        db: Session,
        image_id: int,
    ) -> ProductImage:

        image = db.get(
            ProductImage,
            image_id,
        )

        if image is None:
            raise LookupError(
                "Imagen no encontrada."
            )

        return image


    # =====================================================
    # QUITAR PRINCIPAL ANTERIOR
    # =====================================================

    @staticmethod
    def _clear_primary(
        db: Session,
        product_id: int,
        exclude_id: int | None = None,
    ) -> None:

        query = (
            db.query(ProductImage)
            .filter(
                ProductImage.product_id
                == product_id,
                ProductImage.is_primary
                == True,
            )
        )

        if exclude_id is not None:
            query = query.filter(
                ProductImage.id
                != exclude_id
            )

        for image in query.all():
            image.is_primary = False


    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_image(
        db: Session,
        product_id: int,
        image_url: str,
        cloudinary_public_id: str,
        alt_text: str | None,
        sort_order: int,
        is_primary: bool,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProductImage:

        product = (
            ProductImageService
            ._get_product(
                db=db,
                product_id=product_id,
            )
        )

        if is_primary:
            ProductImageService._clear_primary(
                db=db,
                product_id=product_id,
            )

        image = ProductImage(
            product_id=product_id,
            image_url=image_url,
            cloudinary_public_id=
                cloudinary_public_id,
            alt_text=(
                alt_text.strip()
                if alt_text
                else None
            ),
            sort_order=sort_order,
            is_primary=is_primary,
            is_active=True,
        )

        db.add(image)

        db.flush()

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="CREATE_PRODUCT_IMAGE",
            module="CATALOG",
            entity_type="ProductImage",
            entity_id=image.id,
            description=(
                f"Se agregó una imagen al "
                f"producto '{product.name}'."
            ),
            old_values=None,
            new_values={
                "product_id":
                    image.product_id,
                "image_url":
                    image.image_url,
                "cloudinary_public_id":
                    image.cloudinary_public_id,
                "alt_text":
                    image.alt_text,
                "sort_order":
                    image.sort_order,
                "is_primary":
                    image.is_primary,
                "is_active":
                    image.is_active,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        db.refresh(image)

        return image


    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_image(
        db: Session,
        image_id: int,
        payload: ProductImageUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> ProductImage:

        image = (
            ProductImageService
            .get_image(
                db=db,
                image_id=image_id,
            )
        )

        old_values = {
            "alt_text":
                image.alt_text,
            "sort_order":
                image.sort_order,
            "is_primary":
                image.is_primary,
            "is_active":
                image.is_active,
        }

        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )

        if "alt_text" in update_data:
            value = update_data[
                "alt_text"
            ]

            image.alt_text = (
                value.strip()
                if value
                else None
            )

        if (
            "sort_order" in update_data
            and update_data[
                "sort_order"
            ] is not None
        ):
            image.sort_order = (
                update_data[
                    "sort_order"
                ]
            )

        if (
            update_data.get(
                "is_primary"
            )
            is True
        ):
            ProductImageService._clear_primary(
                db=db,
                product_id=image.product_id,
                exclude_id=image.id,
            )

            image.is_primary = True

        elif (
            "is_primary"
            in update_data
            and update_data[
                "is_primary"
            ] is not None
        ):
            image.is_primary = (
                update_data[
                    "is_primary"
                ]
            )

        if (
            "is_active"
            in update_data
            and update_data[
                "is_active"
            ] is not None
        ):
            image.is_active = (
                update_data[
                    "is_active"
                ]
            )

            if not image.is_active:
                image.is_primary = False

        db.flush()

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="UPDATE_PRODUCT_IMAGE",
            module="CATALOG",
            entity_type="ProductImage",
            entity_id=image.id,
            description=(
                "Se actualizó una imagen "
                "del producto."
            ),
            old_values=old_values,
            new_values={
                "alt_text":
                    image.alt_text,
                "sort_order":
                    image.sort_order,
                "is_primary":
                    image.is_primary,
                "is_active":
                    image.is_active,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        db.refresh(image)

        return image


    # =====================================================
    # ELIMINAR DEFINITIVAMENTE
    # =====================================================

    @staticmethod
    def delete_image(
        db: Session,
        image_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> str | None:

        image = (
            ProductImageService
            .get_image(
                db=db,
                image_id=image_id,
            )
        )

        public_id = (
            image.cloudinary_public_id
        )

        old_values = {
            "product_id":
                image.product_id,
            "image_url":
                image.image_url,
            "cloudinary_public_id":
                image.cloudinary_public_id,
            "alt_text":
                image.alt_text,
            "sort_order":
                image.sort_order,
            "is_primary":
                image.is_primary,
        }

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="DELETE_PRODUCT_IMAGE",
            module="CATALOG",
            entity_type="ProductImage",
            entity_id=image.id,
            description=(
                "Se eliminó una imagen "
                "del producto."
            ),
            old_values=old_values,
            new_values=None,
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.delete(image)

        db.commit()

        return public_id