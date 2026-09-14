import math

from typing import Literal

from sqlalchemy import (
    func,
    or_,
)

from sqlalchemy.orm import Session

from app.models.color import Color

from app.schemas.color import (
    ColorCreate,
    ColorUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class ColorService:

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_colors(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        is_active: bool | None = None,
        sort_by: Literal[
            "id",
            "name",
            "hex_code",
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
            Color
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
                        Color.name.ilike(
                            pattern
                        ),

                        Color.hex_code.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # FILTRO ESTADO
        # =================================================

        if is_active is not None:

            query = query.filter(
                Color.is_active
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
                Color.id,

            "name":
                Color.name,

            "hex_code":
                Color.hex_code,

            "is_active":
                Color.is_active,

            "created_at":
                Color.created_at,

            "updated_at":
                Color.updated_at,
        }

        sort_column = (
            sort_columns[
                sort_by
            ]
        )

        if sort_order == "desc":

            query = query.order_by(
                sort_column.desc(),
                Color.id.desc(),
            )

        else:

            query = query.order_by(
                sort_column.asc(),
                Color.id.asc(),
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
    def get_color(
        db: Session,
        color_id: int,
    ) -> Color:

        color = db.get(
            Color,
            color_id,
        )

        if color is None:

            raise LookupError(
                "Color no encontrado."
            )

        return color

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

        query = (
            db.query(
                Color
            )
            .filter(
                func.lower(
                    Color.name
                )
                ==
                clean_name.lower()
            )
        )

        if exclude_id is not None:

            query = query.filter(
                Color.id != exclude_id
            )

        existing = (
            query.first()
        )

        if existing is not None:

            raise ValueError(
                "Ya existe un color "
                "con ese nombre."
            )

    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_color(
        db: Session,
        payload: ColorCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Color:

        clean_name = (
            payload.name.strip()
        )

        ColorService._validate_unique_name(
            db=db,
            name=clean_name,
        )

        color = Color(
            name=
                clean_name,

            hex_code=
                payload.hex_code,

            is_active=
                True,
        )

        db.add(
            color
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
                "CREATE_COLOR",

            module=
                "CATALOG",

            entity_type=
                "Color",

            entity_id=
                color.id,

            description=(
                f"Se creó el color "
                f"'{color.name}'."
            ),

            old_values=
                None,

            new_values={
                "name":
                    color.name,

                "hex_code":
                    color.hex_code,

                "is_active":
                    color.is_active,
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
            color
        )

        return color

    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_color(
        db: Session,
        color_id: int,
        payload: ColorUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Color:

        color = (
            ColorService
            .get_color(
                db=db,
                color_id=
                    color_id,
            )
        )

        old_values = {
            "name":
                color.name,

            "hex_code":
                color.hex_code,

            "is_active":
                color.is_active,
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

            ColorService._validate_unique_name(
                db=db,
                name=clean_name,
                exclude_id=
                    color.id,
            )

            color.name = (
                clean_name
            )

        # =================================================
        # HEX
        # =================================================

        if (
            "hex_code"
            in update_data
        ):

            color.hex_code = (
                update_data[
                    "hex_code"
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

            color.is_active = (
                update_data[
                    "is_active"
                ]
            )

        db.flush()

        new_values = {
            "name":
                color.name,

            "hex_code":
                color.hex_code,

            "is_active":
                color.is_active,
        }

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_COLOR",

            module=
                "CATALOG",

            entity_type=
                "Color",

            entity_id=
                color.id,

            description=(
                f"Se actualizó el color "
                f"'{color.name}'."
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
            color
        )

        return color

    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_color(
        db: Session,
        color_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Color:

        color = (
            ColorService
            .get_color(
                db=db,
                color_id=
                    color_id,
            )
        )

        if not color.is_active:

            raise ValueError(
                "El color ya se encuentra inactivo."
            )

        color.is_active = (
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
                "DEACTIVATE_COLOR",

            module=
                "CATALOG",

            entity_type=
                "Color",

            entity_id=
                color.id,

            description=(
                f"Se desactivó el color "
                f"'{color.name}'."
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
            color
        )

        return color