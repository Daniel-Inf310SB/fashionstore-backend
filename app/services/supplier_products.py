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

from app.models.product import Product
from app.models.supplier import Supplier
from app.models.supplier_product import (
    SupplierProduct,
)

from app.schemas.supplier_product import (
    SupplierProductCreate,
    SupplierProductUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class SupplierProductService:

    # =====================================================
    # LIMPIAR TEXTO OPCIONAL
    # =====================================================

    @staticmethod
    def _clean_optional(
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        return (
            value
            if value
            else None
        )


    # =====================================================
    # OBTENER PROVEEDOR
    # =====================================================

    @staticmethod
    def _get_supplier(
        db: Session,
        supplier_id: int,
    ) -> Supplier:

        supplier = db.get(
            Supplier,
            supplier_id,
        )

        if supplier is None:

            raise LookupError(
                "Proveedor no encontrado."
            )

        return supplier


    # =====================================================
    # OBTENER PRODUCTO
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
    def get_supplier_products(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        supplier_id: int | None = None,
        product_id: int | None = None,
        is_active: bool | None = None,
        sort_by: str = "created_at",
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
            db.query(
                SupplierProduct
            )
            .join(
                Supplier,
                SupplierProduct.supplier_id
                == Supplier.id,
            )
            .join(
                Product,
                SupplierProduct.product_id
                == Product.id,
            )
            .options(
                joinedload(
                    SupplierProduct.supplier
                ),
                joinedload(
                    SupplierProduct.product
                ),
            )
        )


        # =================================================
        # BUSCAR
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
                    )
                )


        # =================================================
        # PROVEEDOR
        # =================================================

        if supplier_id is not None:

            query = query.filter(
                SupplierProduct.supplier_id
                == supplier_id
            )


        # =================================================
        # PRODUCTO
        # =================================================

        if product_id is not None:

            query = query.filter(
                SupplierProduct.product_id
                == product_id
            )


        # =================================================
        # ESTADO
        # =================================================

        if is_active is not None:

            query = query.filter(
                SupplierProduct.is_active
                == is_active
            )


        # =================================================
        # TOTAL
        # =================================================

        total = query.count()


        # =================================================
        # ORDENAMIENTO
        # =================================================

        sort_columns = {
            "id":
                SupplierProduct.id,

            "supplier_id":
                SupplierProduct.supplier_id,

            "product_id":
                SupplierProduct.product_id,

            "supplier_code":
                SupplierProduct.supplier_code,

            "purchase_price":
                SupplierProduct.purchase_price,

            "minimum_order_quantity":
                SupplierProduct
                .minimum_order_quantity,

            "lead_time_days":
                SupplierProduct.lead_time_days,

            "is_active":
                SupplierProduct.is_active,

            "created_at":
                SupplierProduct.created_at,

            "updated_at":
                SupplierProduct.updated_at,
        }

        sort_column = (
            sort_columns.get(
                sort_by,
                SupplierProduct.created_at,
            )
        )

        if (
            sort_order.lower()
            == "asc"
        ):

            query = query.order_by(
                sort_column.asc(),
                SupplierProduct.id.asc(),
            )

        else:

            query = query.order_by(
                sort_column.desc(),
                SupplierProduct.id.desc(),
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
                / page_size
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
    def get_supplier_product(
        db: Session,
        supplier_product_id: int,
    ) -> SupplierProduct:

        supplier_product = (
            db.query(
                SupplierProduct
            )
            .options(
                joinedload(
                    SupplierProduct.supplier
                ),
                joinedload(
                    SupplierProduct.product
                ),
            )
            .filter(
                SupplierProduct.id
                == supplier_product_id
            )
            .first()
        )

        if supplier_product is None:

            raise LookupError(
                "Producto del proveedor "
                "no encontrado."
            )

        return supplier_product


    # =====================================================
    # VALIDAR DUPLICADO
    # =====================================================

    @staticmethod
    def _validate_unique_relation(
        db: Session,
        supplier_id: int,
        product_id: int,
    ) -> None:

        existing = (
            db.query(
                SupplierProduct
            )
            .filter(
                SupplierProduct.supplier_id
                == supplier_id,

                SupplierProduct.product_id
                == product_id,
            )
            .first()
        )

        if existing is not None:

            raise ValueError(
                "Este producto ya está "
                "asociado al proveedor."
            )


    # =====================================================
    # VALIDAR CÓDIGO DEL PROVEEDOR
    # =====================================================

    @staticmethod
    def _validate_supplier_code(
        db: Session,
        supplier_id: int,
        supplier_code: str | None,
        exclude_id: int | None = None,
    ) -> None:

        if supplier_code is None:

            return

        query = (
            db.query(
                SupplierProduct
            )
            .filter(
                SupplierProduct.supplier_id
                == supplier_id,

                func.lower(
                    SupplierProduct.supplier_code
                )
                ==
                supplier_code.lower(),
            )
        )

        if exclude_id is not None:

            query = query.filter(
                SupplierProduct.id
                != exclude_id
            )

        existing = query.first()

        if existing is not None:

            raise ValueError(
                "El código del proveedor "
                "ya está registrado."
            )


    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_supplier_product(
        db: Session,
        payload: SupplierProductCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SupplierProduct:

        supplier = (
            SupplierProductService
            ._get_supplier(
                db=db,
                supplier_id=
                    payload.supplier_id,
            )
        )

        product = (
            SupplierProductService
            ._get_product(
                db=db,
                product_id=
                    payload.product_id,
            )
        )

        if not supplier.is_active:

            raise ValueError(
                "El proveedor está inactivo."
            )

        if not product.is_active:

            raise ValueError(
                "El producto está inactivo."
            )


        SupplierProductService \
            ._validate_unique_relation(
                db=db,
                supplier_id=
                    payload.supplier_id,
                product_id=
                    payload.product_id,
            )


        supplier_code = (
            SupplierProductService
            ._clean_optional(
                payload.supplier_code
            )
        )


        SupplierProductService \
            ._validate_supplier_code(
                db=db,
                supplier_id=
                    payload.supplier_id,
                supplier_code=
                    supplier_code,
            )


        supplier_product = (
            SupplierProduct(
                supplier_id=
                    payload.supplier_id,

                product_id=
                    payload.product_id,

                supplier_code=
                    supplier_code,

                purchase_price=
                    payload.purchase_price,

                minimum_order_quantity=
                    payload
                    .minimum_order_quantity,

                lead_time_days=
                    payload.lead_time_days,

                is_active=
                    True,
            )
        )


        db.add(
            supplier_product
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
                "CREATE_SUPPLIER_PRODUCT",

            module=
                "SUPPLIERS",

            entity_type=
                "SupplierProduct",

            entity_id=
                supplier_product.id,

            description=(
                f"Se asoció el producto "
                f"'{product.name}' al proveedor "
                f"'{supplier.name}'."
            ),

            old_values=None,

            new_values={
                "supplier_id":
                    supplier_product
                    .supplier_id,

                "product_id":
                    supplier_product
                    .product_id,

                "supplier_code":
                    supplier_product
                    .supplier_code,

                "purchase_price":
                    str(
                        supplier_product
                        .purchase_price
                    ),

                "minimum_order_quantity":
                    supplier_product
                    .minimum_order_quantity,

                "lead_time_days":
                    supplier_product
                    .lead_time_days,

                "is_active":
                    supplier_product
                    .is_active,
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
            SupplierProductService
            .get_supplier_product(
                db=db,
                supplier_product_id=
                    supplier_product.id,
            )
        )


    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_supplier_product(
        db: Session,
        supplier_product_id: int,
        payload: SupplierProductUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SupplierProduct:

        supplier_product = (
            SupplierProductService
            .get_supplier_product(
                db=db,
                supplier_product_id=
                    supplier_product_id,
            )
        )


        old_values = {
            "supplier_code":
                supplier_product
                .supplier_code,

            "purchase_price":
                str(
                    supplier_product
                    .purchase_price
                ),

            "minimum_order_quantity":
                supplier_product
                .minimum_order_quantity,

            "lead_time_days":
                supplier_product
                .lead_time_days,

            "is_active":
                supplier_product
                .is_active,
        }


        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )


        # =================================================
        # CÓDIGO
        # =================================================

        if (
            "supplier_code"
            in update_data
        ):

            supplier_code = (
                SupplierProductService
                ._clean_optional(
                    update_data[
                        "supplier_code"
                    ]
                )
            )


            SupplierProductService \
                ._validate_supplier_code(
                    db=db,
                    supplier_id=
                        supplier_product
                        .supplier_id,
                    supplier_code=
                        supplier_code,
                    exclude_id=
                        supplier_product.id,
                )


            supplier_product \
                .supplier_code = (
                    supplier_code
                )


        # =================================================
        # PRECIO
        # =================================================

        if (
            "purchase_price"
            in update_data
            and
            update_data[
                "purchase_price"
            ] is not None
        ):

            supplier_product \
                .purchase_price = (
                    update_data[
                        "purchase_price"
                    ]
                )


        # =================================================
        # PEDIDO MÍNIMO
        # =================================================

        if (
            "minimum_order_quantity"
            in update_data
            and
            update_data[
                "minimum_order_quantity"
            ] is not None
        ):

            supplier_product \
                .minimum_order_quantity = (
                    update_data[
                        "minimum_order_quantity"
                    ]
                )


        # =================================================
        # TIEMPO ENTREGA
        # =================================================

        if (
            "lead_time_days"
            in update_data
            and
            update_data[
                "lead_time_days"
            ] is not None
        ):

            supplier_product \
                .lead_time_days = (
                    update_data[
                        "lead_time_days"
                    ]
                )


        # =================================================
        # ESTADO
        # =================================================

        if (
            "is_active"
            in update_data
            and
            update_data[
                "is_active"
            ] is not None
        ):

            supplier_product \
                .is_active = (
                    update_data[
                        "is_active"
                    ]
                )


        db.flush()


        new_values = {
            "supplier_code":
                supplier_product
                .supplier_code,

            "purchase_price":
                str(
                    supplier_product
                    .purchase_price
                ),

            "minimum_order_quantity":
                supplier_product
                .minimum_order_quantity,

            "lead_time_days":
                supplier_product
                .lead_time_days,

            "is_active":
                supplier_product
                .is_active,
        }


        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_SUPPLIER_PRODUCT",

            module=
                "SUPPLIERS",

            entity_type=
                "SupplierProduct",

            entity_id=
                supplier_product.id,

            description=(
                "Se actualizó un producto "
                "asociado a proveedor."
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
            SupplierProductService
            .get_supplier_product(
                db=db,
                supplier_product_id=
                    supplier_product.id,
            )
        )


    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_supplier_product(
        db: Session,
        supplier_product_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> SupplierProduct:

        supplier_product = (
            SupplierProductService
            .get_supplier_product(
                db=db,
                supplier_product_id=
                    supplier_product_id,
            )
        )


        if not supplier_product.is_active:

            raise ValueError(
                "El producto del proveedor "
                "ya se encuentra inactivo."
            )


        supplier_product.is_active = (
            False
        )


        db.flush()


        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "DEACTIVATE_SUPPLIER_PRODUCT",

            module=
                "SUPPLIERS",

            entity_type=
                "SupplierProduct",

            entity_id=
                supplier_product.id,

            description=(
                "Se desactivó un producto "
                "del proveedor."
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
            SupplierProductService
            .get_supplier_product(
                db=db,
                supplier_product_id=
                    supplier_product.id,
            )
        )