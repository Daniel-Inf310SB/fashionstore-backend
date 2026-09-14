from __future__ import annotations

import math

from typing import Literal

from sqlalchemy import (
    func,
    or_,
)

from sqlalchemy.orm import Session

from app.models.supplier import Supplier

from app.schemas.supplier import (
    SupplierCreate,
    SupplierUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class SupplierService:

    # =====================================================
    # UTILIDADES
    # =====================================================

    @staticmethod
    def _clean_optional(
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        clean_value = value.strip()

        return (
            clean_value
            if clean_value
            else None
        )

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_suppliers(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        is_active: bool | None = None,
        sort_by: Literal[
            "id",
            "name",
            "business_name",
            "nit",
            "email",
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

        query = db.query(
            Supplier
        )

        # =================================================
        # BUSCADOR
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
                        Supplier.business_name.ilike(
                            pattern
                        ),
                        Supplier.nit.ilike(
                            pattern
                        ),
                        Supplier.phone.ilike(
                            pattern
                        ),
                        Supplier.email.ilike(
                            pattern
                        ),
                        Supplier.address.ilike(
                            pattern
                        ),
                        Supplier.contact_name.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # ESTADO
        # =================================================

        if is_active is not None:

            query = query.filter(
                Supplier.is_active
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
                Supplier.id,

            "name":
                Supplier.name,

            "business_name":
                Supplier.business_name,

            "nit":
                Supplier.nit,

            "email":
                Supplier.email,

            "is_active":
                Supplier.is_active,

            "created_at":
                Supplier.created_at,

            "updated_at":
                Supplier.updated_at,
        }

        sort_column = (
            sort_columns[
                sort_by
            ]
        )

        if sort_order == "desc":

            query = query.order_by(
                sort_column.desc(),
                Supplier.id.desc(),
            )

        else:

            query = query.order_by(
                sort_column.asc(),
                Supplier.id.asc(),
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
    # OBTENER POR ID
    # =====================================================

    @staticmethod
    def get_supplier(
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
    # VALIDAR NIT ÚNICO
    # =====================================================

    @staticmethod
    def _validate_unique_nit(
        db: Session,
        nit: str,
        exclude_id: int | None = None,
    ) -> None:

        clean_nit = (
            nit.strip()
        )

        query = (
            db.query(
                Supplier
            )
            .filter(
                func.lower(
                    Supplier.nit
                )
                ==
                clean_nit.lower()
            )
        )

        if exclude_id is not None:

            query = query.filter(
                Supplier.id
                != exclude_id
            )

        existing = (
            query.first()
        )

        if existing is not None:

            raise ValueError(
                "Ya existe un proveedor "
                "con ese NIT."
            )

    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_supplier(
        db: Session,
        payload: SupplierCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Supplier:

        clean_name = (
            payload.name.strip()
        )

        clean_nit = (
            payload.nit.strip()
        )

        SupplierService._validate_unique_nit(
            db=db,
            nit=clean_nit,
        )

        supplier = Supplier(
            name=
                clean_name,

            business_name=
                SupplierService._clean_optional(
                    payload.business_name
                ),

            nit=
                clean_nit,

            phone=
                SupplierService._clean_optional(
                    payload.phone
                ),

            email=
                SupplierService._clean_optional(
                    payload.email
                ),

            address=
                SupplierService._clean_optional(
                    payload.address
                ),

            contact_name=
                SupplierService._clean_optional(
                    payload.contact_name
                ),

            is_active=
                True,
        )

        db.add(
            supplier
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
                "CREATE_SUPPLIER",

            module=
                "SUPPLIERS",

            entity_type=
                "Supplier",

            entity_id=
                supplier.id,

            description=(
                f"Se creó el proveedor "
                f"'{supplier.name}'."
            ),

            old_values=None,

            new_values={
                "name":
                    supplier.name,

                "business_name":
                    supplier.business_name,

                "nit":
                    supplier.nit,

                "phone":
                    supplier.phone,

                "email":
                    supplier.email,

                "address":
                    supplier.address,

                "contact_name":
                    supplier.contact_name,

                "is_active":
                    supplier.is_active,
            },

            ip_address=
                ip_address,

            user_agent=
                user_agent,

            status=
                "SUCCESS",
        )

        db.commit()

        db.refresh(
            supplier
        )

        return supplier

    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_supplier(
        db: Session,
        supplier_id: int,
        payload: SupplierUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Supplier:

        supplier = (
            SupplierService
            .get_supplier(
                db=db,
                supplier_id=
                    supplier_id,
            )
        )

        old_values = {
            "name":
                supplier.name,

            "business_name":
                supplier.business_name,

            "nit":
                supplier.nit,

            "phone":
                supplier.phone,

            "email":
                supplier.email,

            "address":
                supplier.address,

            "contact_name":
                supplier.contact_name,

            "is_active":
                supplier.is_active,
        }

        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )

        # =================================================
        # NOMBRE
        # =================================================

        if (
            "name" in update_data
            and update_data["name"]
            is not None
        ):

            supplier.name = (
                update_data[
                    "name"
                ].strip()
            )

        # =================================================
        # NIT
        # =================================================

        if (
            "nit" in update_data
            and update_data["nit"]
            is not None
        ):

            clean_nit = (
                update_data[
                    "nit"
                ].strip()
            )

            SupplierService._validate_unique_nit(
                db=db,
                nit=clean_nit,
                exclude_id=
                    supplier.id,
            )

            supplier.nit = (
                clean_nit
            )

        # =================================================
        # CAMPOS OPCIONALES
        # =================================================

        optional_fields = (
            "business_name",
            "phone",
            "email",
            "address",
            "contact_name",
        )

        for field_name in optional_fields:

            if field_name in update_data:

                setattr(
                    supplier,
                    field_name,
                    SupplierService
                    ._clean_optional(
                        update_data[
                            field_name
                        ]
                    ),
                )

        # =================================================
        # ESTADO
        # =================================================

        if (
            "is_active" in update_data
            and update_data[
                "is_active"
            ]
            is not None
        ):

            supplier.is_active = (
                update_data[
                    "is_active"
                ]
            )

        db.flush()

        new_values = {
            "name":
                supplier.name,

            "business_name":
                supplier.business_name,

            "nit":
                supplier.nit,

            "phone":
                supplier.phone,

            "email":
                supplier.email,

            "address":
                supplier.address,

            "contact_name":
                supplier.contact_name,

            "is_active":
                supplier.is_active,
        }

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_SUPPLIER",

            module=
                "SUPPLIERS",

            entity_type=
                "Supplier",

            entity_id=
                supplier.id,

            description=(
                f"Se actualizó el proveedor "
                f"'{supplier.name}'."
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

        db.refresh(
            supplier
        )

        return supplier

    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_supplier(
        db: Session,
        supplier_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Supplier:

        supplier = (
            SupplierService
            .get_supplier(
                db=db,
                supplier_id=
                    supplier_id,
            )
        )

        if not supplier.is_active:

            raise ValueError(
                "El proveedor ya se encuentra inactivo."
            )

        old_values = {
            "is_active":
                True,
        }

        supplier.is_active = (
            False
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
                "DEACTIVATE_SUPPLIER",

            module=
                "SUPPLIERS",

            entity_type=
                "Supplier",

            entity_id=
                supplier.id,

            description=(
                f"Se desactivó el proveedor "
                f"'{supplier.name}'."
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

        db.refresh(
            supplier
        )

        return supplier
