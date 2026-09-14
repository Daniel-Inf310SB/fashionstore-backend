import math

from typing import Literal

from sqlalchemy import (
    func,
    or_,
)

from sqlalchemy.orm import Session

from app.models.audience import Audience

from app.schemas.audience import (
    AudienceCreate,
    AudienceUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class AudienceService:

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_audiences(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        is_active: bool | None = None,
        sort_by: Literal[
            "id",
            "name",
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
            Audience
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
                        Audience.name.ilike(
                            pattern
                        ),
                        Audience.description.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # ESTADO
        # =================================================

        if is_active is not None:

            query = query.filter(
                Audience.is_active
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
                Audience.id,

            "name":
                Audience.name,

            "is_active":
                Audience.is_active,

            "created_at":
                Audience.created_at,

            "updated_at":
                Audience.updated_at,
        }

        sort_column = (
            sort_columns[
                sort_by
            ]
        )

        if sort_order == "desc":

            query = query.order_by(
                sort_column.desc(),
                Audience.id.desc(),
            )

        else:

            query = query.order_by(
                sort_column.asc(),
                Audience.id.asc(),
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
    def get_audience(
        db: Session,
        audience_id: int,
    ) -> Audience:

        audience = db.get(
            Audience,
            audience_id,
        )

        if audience is None:

            raise LookupError(
                "Audiencia no encontrada."
            )

        return audience

    # =====================================================
    # VALIDAR NOMBRE ÚNICO
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
                Audience
            )
            .filter(
                func.lower(
                    Audience.name
                )
                ==
                clean_name.lower()
            )
        )

        if exclude_id is not None:

            query = query.filter(
                Audience.id != exclude_id
            )

        existing = (
            query.first()
        )

        if existing is not None:

            raise ValueError(
                "Ya existe una audiencia "
                "con ese nombre."
            )

    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_audience(
        db: Session,
        payload: AudienceCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Audience:

        clean_name = (
            payload.name.strip()
        )

        clean_description = (
            payload.description.strip()
            if payload.description
            else None
        )

        AudienceService._validate_unique_name(
            db=db,
            name=clean_name,
        )

        audience = Audience(
            name=clean_name,

            description=
                clean_description,

            is_active=True,
        )

        db.add(
            audience
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
                "CREATE_AUDIENCE",

            module=
                "CATALOG",

            entity_type=
                "Audience",

            entity_id=
                audience.id,

            description=(
                f"Se creó la audiencia "
                f"'{audience.name}'."
            ),

            old_values=None,

            new_values={
                "name":
                    audience.name,

                "description":
                    audience.description,

                "is_active":
                    audience.is_active,
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
            audience
        )

        return audience

    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_audience(
        db: Session,
        audience_id: int,
        payload: AudienceUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Audience:

        audience = (
            AudienceService
            .get_audience(
                db=db,
                audience_id=
                    audience_id,
            )
        )

        old_values = {
            "name":
                audience.name,

            "description":
                audience.description,

            "is_active":
                audience.is_active,
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

            AudienceService._validate_unique_name(
                db=db,
                name=clean_name,
                exclude_id=
                    audience.id,
            )

            audience.name = (
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

            audience.description = (
                description.strip()
                if description
                else None
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

            audience.is_active = (
                update_data[
                    "is_active"
                ]
            )

        db.flush()

        new_values = {
            "name":
                audience.name,

            "description":
                audience.description,

            "is_active":
                audience.is_active,
        }

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_AUDIENCE",

            module=
                "CATALOG",

            entity_type=
                "Audience",

            entity_id=
                audience.id,

            description=(
                f"Se actualizó la audiencia "
                f"'{audience.name}'."
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
            audience
        )

        return audience

    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_audience(
        db: Session,
        audience_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Audience:

        audience = (
            AudienceService
            .get_audience(
                db=db,
                audience_id=
                    audience_id,
            )
        )

        if not audience.is_active:

            raise ValueError(
                "La audiencia ya se encuentra inactiva."
            )

        audience.is_active = False

        db.flush()

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "DEACTIVATE_AUDIENCE",

            module=
                "CATALOG",

            entity_type=
                "Audience",

            entity_id=
                audience.id,

            description=(
                f"Se desactivó la audiencia "
                f"'{audience.name}'."
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
            audience
        )

        return audience