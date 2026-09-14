import math

from typing import Literal

from sqlalchemy import (
    func,
    or_,
)
from sqlalchemy.orm import Session

from app.models.size import Size

from app.schemas.size import (
    SizeCreate,
    SizeUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class SizeService:

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_sizes(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        is_active: bool | None = None,
        sort_by: Literal[
            "id",
            "name",
            "sort_order",
            "is_active",
            "created_at",
            "updated_at",
        ] = "sort_order",
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
            Size
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
                        Size.name.ilike(
                            pattern
                        ),
                        Size.description.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # ESTADO
        # =================================================

        if is_active is not None:

            query = query.filter(
                Size.is_active
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
                Size.id,

            "name":
                Size.name,

            "sort_order":
                Size.sort_order,

            "is_active":
                Size.is_active,

            "created_at":
                Size.created_at,

            "updated_at":
                Size.updated_at,
        }

        sort_column = (
            sort_columns[
                sort_by
            ]
        )

        if sort_order == "desc":

            query = query.order_by(
                sort_column.desc(),
                Size.id.desc(),
            )

        else:

            query = query.order_by(
                sort_column.asc(),
                Size.id.asc(),
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
    # OBTENER
    # =====================================================

    @staticmethod
    def get_size(
        db: Session,
        size_id: int,
    ) -> Size:

        size = db.get(
            Size,
            size_id,
        )

        if size is None:

            raise LookupError(
                "Talla no encontrada."
            )

        return size

    # =====================================================
    # VALIDAR NOMBRE
    # =====================================================

    @staticmethod
    def _validate_unique_name(
        db: Session,
        name: str,
        exclude_id: int | None = None,
    ) -> None:

        clean_name = (
            name.strip()
        )

        query = db.query(
            Size
        ).filter(
            func.lower(
                Size.name
            )
            ==
            clean_name.lower()
        )

        if exclude_id is not None:

            query = query.filter(
                Size.id != exclude_id
            )

        existing = (
            query.first()
        )

        if existing is not None:

            raise ValueError(
                "Ya existe una talla "
                "con ese nombre."
            )

    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_size(
        db: Session,
        payload: SizeCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Size:

        clean_name = (
            payload.name.strip()
        )

        clean_description = (
            payload.description.strip()
            if payload.description
            else None
        )

        SizeService._validate_unique_name(
            db=db,
            name=clean_name,
        )

        size = Size(
            name=clean_name,

            description=
                clean_description,

            sort_order=
                payload.sort_order,

            is_active=True,
        )

        db.add(
            size
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
                "CREATE_SIZE",

            module=
                "CATALOG",

            entity_type=
                "Size",

            entity_id=
                size.id,

            description=(
                f"Se creó la talla "
                f"'{size.name}'."
            ),

            old_values=None,

            new_values={
                "name":
                    size.name,

                "description":
                    size.description,

                "sort_order":
                    size.sort_order,

                "is_active":
                    size.is_active,
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
            size
        )

        return size

    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_size(
        db: Session,
        size_id: int,
        payload: SizeUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Size:

        size = (
            SizeService
            .get_size(
                db=db,
                size_id=
                    size_id,
            )
        )

        old_values = {
            "name":
                size.name,

            "description":
                size.description,

            "sort_order":
                size.sort_order,

            "is_active":
                size.is_active,
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
            and update_data[
                "name"
            ] is not None
        ):

            clean_name = (
                update_data[
                    "name"
                ].strip()
            )

            SizeService._validate_unique_name(
                db=db,
                name=clean_name,
                exclude_id=
                    size.id,
            )

            size.name = (
                clean_name
            )

        # =================================================
        # DESCRIPCIÓN
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

            size.description = (
                description.strip()
                if description
                else None
            )

        # =================================================
        # ORDEN
        # =================================================

        if (
            "sort_order"
            in update_data
            and update_data[
                "sort_order"
            ] is not None
        ):

            size.sort_order = (
                update_data[
                    "sort_order"
                ]
            )

        # =================================================
        # ESTADO
        # =================================================

        if (
            "is_active"
            in update_data
            and update_data[
                "is_active"
            ] is not None
        ):

            size.is_active = (
                update_data[
                    "is_active"
                ]
            )

        db.flush()

        new_values = {
            "name":
                size.name,

            "description":
                size.description,

            "sort_order":
                size.sort_order,

            "is_active":
                size.is_active,
        }

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_SIZE",

            module=
                "CATALOG",

            entity_type=
                "Size",

            entity_id=
                size.id,

            description=(
                f"Se actualizó la talla "
                f"'{size.name}'."
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
            size
        )

        return size

    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_size(
        db: Session,
        size_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Size:

        size = (
            SizeService
            .get_size(
                db=db,
                size_id=
                    size_id,
            )
        )

        if not size.is_active:

            raise ValueError(
                "La talla ya se encuentra inactiva."
            )

        size.is_active = False

        db.flush()

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "DEACTIVATE_SIZE",

            module=
                "CATALOG",

            entity_type=
                "Size",

            entity_id=
                size.id,

            description=(
                f"Se desactivó la talla "
                f"'{size.name}'."
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

        db.refresh(
            size
        )

        return size