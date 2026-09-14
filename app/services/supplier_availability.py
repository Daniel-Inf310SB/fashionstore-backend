from __future__ import annotations

import math

from datetime import datetime, timezone

from sqlalchemy import (
    or_,
)

from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.supplier_availability import (
    SupplierAvailability,
)

from app.models.supplier_product import (
    SupplierProduct,
)

from app.models.supplier import (
    Supplier,
)

from app.models.product import (
    Product,
)

from app.models.product_variant import (
    ProductVariant,
)

from app.schemas.supplier_availability import (
    SupplierAvailabilityCreate,
    SupplierAvailabilityUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class SupplierAvailabilityService:

    # =====================================================
    # QUERY BASE
    # =====================================================

    @staticmethod
    def _base_query(
        db: Session,
    ):

        return (
            db.query(
                SupplierAvailability
            )
            .join(
                SupplierProduct,
                SupplierAvailability
                .supplier_product_id
                ==
                SupplierProduct.id,
            )
            .join(
                Supplier,
                SupplierProduct.supplier_id
                ==
                Supplier.id,
            )
            .join(
                Product,
                SupplierProduct.product_id
                ==
                Product.id,
            )
            .join(
                ProductVariant,
                SupplierAvailability
                .product_variant_id
                ==
                ProductVariant.id,
            )
            .options(
                joinedload(
                    SupplierAvailability
                    .supplier_product
                )
                .joinedload(
                    SupplierProduct.supplier
                ),

                joinedload(
                    SupplierAvailability
                    .supplier_product
                )
                .joinedload(
                    SupplierProduct.product
                ),

                joinedload(
                    SupplierAvailability
                    .product_variant
                )
                .joinedload(
                    ProductVariant.size
                ),

                joinedload(
                    SupplierAvailability
                    .product_variant
                )
                .joinedload(
                    ProductVariant.color
                ),
            )
        )


    # =====================================================
    # OBTENER PRODUCTO DEL PROVEEDOR
    # =====================================================

    @staticmethod
    def _get_supplier_product(
        db: Session,
        supplier_product_id: int,
    ) -> SupplierProduct:

        supplier_product = (
            db.get(
                SupplierProduct,
                supplier_product_id,
            )
        )

        if supplier_product is None:

            raise LookupError(
                "Producto del proveedor "
                "no encontrado."
            )

        return supplier_product


    # =====================================================
    # OBTENER VARIANTE
    # =====================================================

    @staticmethod
    def _get_product_variant(
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
                "Variante del producto "
                "no encontrada."
            )

        return variant


    # =====================================================
    # VALIDAR RELACIÓN
    # =====================================================

    @staticmethod
    def _validate_variant_product(
        supplier_product:
            SupplierProduct,

        variant:
            ProductVariant,
    ) -> None:

        if (
            variant.product_id
            !=
            supplier_product.product_id
        ):

            raise ValueError(
                "La variante seleccionada "
                "no pertenece al producto "
                "asociado al proveedor."
            )


    # =====================================================
    # VALIDAR DUPLICADO
    # =====================================================

    @staticmethod
    def _validate_unique_availability(
        db: Session,

        supplier_product_id: int,

        product_variant_id: int,
    ) -> None:

        existing = (
            db.query(
                SupplierAvailability
            )
            .filter(
                SupplierAvailability
                .supplier_product_id
                ==
                supplier_product_id,

                SupplierAvailability
                .product_variant_id
                ==
                product_variant_id,
            )
            .first()
        )

        if existing is not None:

            raise ValueError(
                "Ya existe disponibilidad "
                "registrada para esta variante "
                "y este proveedor."
            )


    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_availabilities(
        db: Session,

        page: int = 1,

        page_size: int = 10,

        search: str | None = None,

        supplier_id: int | None = None,

        supplier_product_id:
            int | None = None,

        product_id:
            int | None = None,

        product_variant_id:
            int | None = None,

        status: str | None = None,

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
            SupplierAvailabilityService
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
                        Supplier.name.ilike(
                            pattern
                        ),

                        Supplier.nit.ilike(
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

                        SupplierProduct
                        .supplier_code
                        .ilike(
                            pattern
                        ),

                        ProductVariant.sku.ilike(
                            pattern
                        ),
                    )
                )


        # =================================================
        # PROVEEDOR
        # =================================================

        if supplier_id is not None:

            query = query.filter(
                SupplierProduct.supplier_id
                ==
                supplier_id
            )


        # =================================================
        # PRODUCTO DEL PROVEEDOR
        # =================================================

        if (
            supplier_product_id
            is not None
        ):

            query = query.filter(
                SupplierAvailability
                .supplier_product_id
                ==
                supplier_product_id
            )


        # =================================================
        # PRODUCTO
        # =================================================

        if product_id is not None:

            query = query.filter(
                SupplierProduct.product_id
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
                SupplierAvailability
                .product_variant_id
                ==
                product_variant_id
            )


        # =================================================
        # ESTADO
        # =================================================

        if status is not None:

            query = query.filter(
                SupplierAvailability.status
                ==
                status
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
                SupplierAvailability.id,

            "supplier_product_id":
                SupplierAvailability
                .supplier_product_id,

            "product_variant_id":
                SupplierAvailability
                .product_variant_id,

            "available_quantity":
                SupplierAvailability
                .available_quantity,

            "status":
                SupplierAvailability.status,

            "purchase_price":
                SupplierAvailability
                .purchase_price,

            "last_checked_at":
                SupplierAvailability
                .last_checked_at,

            "created_at":
                SupplierAvailability
                .created_at,

            "updated_at":
                SupplierAvailability
                .updated_at,
        }


        sort_column = (
            sort_columns.get(
                sort_by,
                SupplierAvailability
                .updated_at,
            )
        )


        if (
            sort_order.lower()
            ==
            "asc"
        ):

            query = query.order_by(
                sort_column.asc(),
                SupplierAvailability.id.asc(),
            )

        else:

            query = query.order_by(
                sort_column.desc(),
                SupplierAvailability.id.desc(),
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
    def get_availability(
        db: Session,

        availability_id: int,
    ) -> SupplierAvailability:

        availability = (
            SupplierAvailabilityService
            ._base_query(
                db
            )
            .filter(
                SupplierAvailability.id
                ==
                availability_id
            )
            .first()
        )


        if availability is None:

            raise LookupError(
                "Disponibilidad del proveedor "
                "no encontrada."
            )


        return availability


    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_availability(
        db: Session,

        payload:
            SupplierAvailabilityCreate,

        user_id:
            int | None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> SupplierAvailability:

        supplier_product = (
            SupplierAvailabilityService
            ._get_supplier_product(
                db=db,

                supplier_product_id=
                    payload
                    .supplier_product_id,
            )
        )


        if not supplier_product.is_active:

            raise ValueError(
                "La asociación del producto "
                "con el proveedor está inactiva."
            )


        variant = (
            SupplierAvailabilityService
            ._get_product_variant(
                db=db,

                product_variant_id=
                    payload
                    .product_variant_id,
            )
        )


        if not variant.is_active:

            raise ValueError(
                "La variante seleccionada "
                "se encuentra inactiva."
            )


        SupplierAvailabilityService \
            ._validate_variant_product(
                supplier_product=
                    supplier_product,

                variant=
                    variant,
            )


        SupplierAvailabilityService \
            ._validate_unique_availability(
                db=db,

                supplier_product_id=
                    payload
                    .supplier_product_id,

                product_variant_id=
                    payload
                    .product_variant_id,
            )


        # =================================================
        # COHERENCIA CANTIDAD / ESTADO
        # =================================================

        if (
            payload.available_quantity
            ==
            0
            and
            payload.status
            !=
            "OUT_OF_STOCK"
        ):

            raise ValueError(
                "Si la cantidad disponible "
                "es 0, el estado debe ser "
                "OUT_OF_STOCK."
            )


        if (
            payload.available_quantity
            >
            0
            and
            payload.status
            ==
            "OUT_OF_STOCK"
        ):

            raise ValueError(
                "Una variante con existencias "
                "no puede tener estado "
                "OUT_OF_STOCK."
            )


        availability = (
            SupplierAvailability(
                supplier_product_id=
                    payload
                    .supplier_product_id,

                product_variant_id=
                    payload
                    .product_variant_id,

                available_quantity=
                    payload
                    .available_quantity,

                status=
                    payload.status,

                purchase_price=
                    payload.purchase_price,

                last_checked_at=
                    datetime.now(
                        timezone.utc
                    ),
            )
        )


        db.add(
            availability
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
                "CREATE_SUPPLIER_AVAILABILITY",

            module=
                "SUPPLIERS",

            entity_type=
                "SupplierAvailability",

            entity_id=
                availability.id,

            description=(
                "Se registró disponibilidad "
                "para una variante del proveedor."
            ),

            old_values=None,

            new_values={
                "supplier_product_id":
                    availability
                    .supplier_product_id,

                "product_variant_id":
                    availability
                    .product_variant_id,

                "available_quantity":
                    availability
                    .available_quantity,

                "status":
                    availability.status,

                "purchase_price":
                    (
                        str(
                            availability
                            .purchase_price
                        )
                        if availability
                        .purchase_price
                        is not None
                        else None
                    ),
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
            SupplierAvailabilityService
            .get_availability(
                db=db,

                availability_id=
                    availability.id,
            )
        )


    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_availability(
        db: Session,

        availability_id: int,

        payload:
            SupplierAvailabilityUpdate,

        user_id:
            int | None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> SupplierAvailability:

        availability = (
            SupplierAvailabilityService
            .get_availability(
                db=db,

                availability_id=
                    availability_id,
            )
        )


        old_values = {
            "available_quantity":
                availability
                .available_quantity,

            "status":
                availability.status,

            "purchase_price":
                (
                    str(
                        availability
                        .purchase_price
                    )
                    if availability
                    .purchase_price
                    is not None
                    else None
                ),
        }


        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )


        # =================================================
        # VALORES FINALES
        # =================================================

        final_quantity = (
            update_data.get(
                "available_quantity",
                availability
                .available_quantity,
            )
        )


        final_status = (
            update_data.get(
                "status",
                availability.status,
            )
        )


        # =================================================
        # COHERENCIA CANTIDAD / ESTADO
        # =================================================

        if (
            final_quantity
            ==
            0
            and
            final_status
            !=
            "OUT_OF_STOCK"
        ):

            raise ValueError(
                "Si la cantidad disponible "
                "es 0, el estado debe ser "
                "OUT_OF_STOCK."
            )


        if (
            final_quantity
            >
            0
            and
            final_status
            ==
            "OUT_OF_STOCK"
        ):

            raise ValueError(
                "Una variante con existencias "
                "no puede tener estado "
                "OUT_OF_STOCK."
            )


        # =================================================
        # CANTIDAD
        # =================================================

        if (
            "available_quantity"
            in update_data
            and
            update_data[
                "available_quantity"
            ] is not None
        ):

            availability \
                .available_quantity = (
                    update_data[
                        "available_quantity"
                    ]
                )


        # =================================================
        # ESTADO
        # =================================================

        if (
            "status"
            in update_data
            and
            update_data[
                "status"
            ] is not None
        ):

            availability.status = (
                update_data[
                    "status"
                ]
            )


        # =================================================
        # PRECIO
        # =================================================

        if (
            "purchase_price"
            in update_data
        ):

            availability \
                .purchase_price = (
                    update_data[
                        "purchase_price"
                    ]
                )


        availability.last_checked_at = (
            datetime.now(
                timezone.utc
            )
        )


        db.flush()


        new_values = {
            "available_quantity":
                availability
                .available_quantity,

            "status":
                availability.status,

            "purchase_price":
                (
                    str(
                        availability
                        .purchase_price
                    )
                    if availability
                    .purchase_price
                    is not None
                    else None
                ),
        }


        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_SUPPLIER_AVAILABILITY",

            module=
                "SUPPLIERS",

            entity_type=
                "SupplierAvailability",

            entity_id=
                availability.id,

            description=(
                "Se actualizó la disponibilidad "
                "de una variante del proveedor."
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
            SupplierAvailabilityService
            .get_availability(
                db=db,

                availability_id=
                    availability.id,
            )
        )


    # =====================================================
    # ELIMINAR
    # =====================================================

    @staticmethod
    def delete_availability(
        db: Session,

        availability_id: int,

        user_id:
            int | None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> dict:

        availability = (
            SupplierAvailabilityService
            .get_availability(
                db=db,

                availability_id=
                    availability_id,
            )
        )


        old_values = {
            "supplier_product_id":
                availability
                .supplier_product_id,

            "product_variant_id":
                availability
                .product_variant_id,

            "available_quantity":
                availability
                .available_quantity,

            "status":
                availability.status,

            "purchase_price":
                (
                    str(
                        availability
                        .purchase_price
                    )
                    if availability
                    .purchase_price
                    is not None
                    else None
                ),
        }


        availability_id_value = (
            availability.id
        )


        db.delete(
            availability
        )

        db.flush()


        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "DELETE_SUPPLIER_AVAILABILITY",

            module=
                "SUPPLIERS",

            entity_type=
                "SupplierAvailability",

            entity_id=
                availability_id_value,

            description=(
                "Se eliminó un registro "
                "de disponibilidad del proveedor."
            ),

            old_values=
                old_values,

            new_values=None,

            ip_address=
                ip_address,

            user_agent=
                user_agent,

            status=
                "SUCCESS",
        )


        db.commit()


        return {
            "message":
                "Disponibilidad eliminada "
                "correctamente."
        }