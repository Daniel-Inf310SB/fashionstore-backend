import math

from datetime import date
from typing import Literal

from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.models.season import Season

from app.schemas.season import (
    SeasonCreate,
    SeasonUpdate,
)

from app.services.audit_log_service import AuditLogService


from app.services.marketing_notification_service import MarketingNotificationService
class SeasonService:

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_seasons(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        is_active: bool | None = None,
        start_date: date | None = None,
        end_date: date | None = None,
        sort_by: Literal[
            "id",
            "name",
            "start_date",
            "end_date",
            "is_active",
            "created_at",
            "updated_at",
        ] = "name",
        sort_order: Literal[
            "asc",
            "desc",
        ] = "asc",
    ) -> dict:

        page = max(page, 1)

        page_size = max(
            1,
            min(page_size, 100),
        )

        query = db.query(Season)

        # BUSCADOR
        if search:
            clean_search = search.strip()

            if clean_search:
                pattern = f"%{clean_search}%"

                query = query.filter(
                    or_(
                        Season.name.ilike(pattern),
                        Season.description.ilike(pattern),
                    )
                )

        # ESTADO
        if is_active is not None:
            query = query.filter(
                Season.is_active == is_active
            )

        # FECHA INICIAL
        if start_date is not None:
            query = query.filter(
                Season.start_date >= start_date
            )

        # FECHA FINAL
        if end_date is not None:
            query = query.filter(
                Season.end_date <= end_date
            )

        total = query.count()

        sort_columns = {
            "id": Season.id,
            "name": Season.name,
            "start_date": Season.start_date,
            "end_date": Season.end_date,
            "is_active": Season.is_active,
            "created_at": Season.created_at,
            "updated_at": Season.updated_at,
        }

        sort_column = sort_columns[sort_by]

        if sort_order == "desc":
            query = query.order_by(
                sort_column.desc(),
                Season.id.desc(),
            )
        else:
            query = query.order_by(
                sort_column.asc(),
                Season.id.asc(),
            )

        items = (
            query
            .offset(
                (page - 1) * page_size
            )
            .limit(page_size)
            .all()
        )

        total_pages = (
            math.ceil(total / page_size)
            if total > 0
            else 0
        )

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }

    # =====================================================
    # OBTENER
    # =====================================================

    @staticmethod
    def get_season(
        db: Session,
        season_id: int,
    ) -> Season:

        season = db.get(
            Season,
            season_id,
        )

        if season is None:
            raise LookupError(
                "Temporada no encontrada."
            )

        return season

    # =====================================================
    # VALIDAR NOMBRE ÚNICO
    # =====================================================

    @staticmethod
    def _validate_unique_name(
        db: Session,
        name: str,
        exclude_id: int | None = None,
    ) -> None:

        clean_name = name.strip()

        query = (
            db.query(Season)
            .filter(
                func.lower(Season.name)
                == clean_name.lower()
            )
        )

        if exclude_id is not None:
            query = query.filter(
                Season.id != exclude_id
            )

        if query.first() is not None:
            raise ValueError(
                "Ya existe una temporada con ese nombre."
            )

    # =====================================================
    # VALIDAR FECHAS
    # =====================================================

    @staticmethod
    def _validate_dates(
        start_date: date | None,
        end_date: date | None,
    ) -> None:

        if (
            start_date is not None
            and end_date is not None
            and end_date < start_date
        ):
            raise ValueError(
                "La fecha final no puede ser anterior a la fecha inicial."
            )

    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_season(
        db: Session,
        payload: SeasonCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Season:

        clean_name = payload.name.strip()

        clean_description = (
            payload.description.strip()
            if payload.description
            else None
        )

        SeasonService._validate_unique_name(
            db=db,
            name=clean_name,
        )

        SeasonService._validate_dates(
            payload.start_date,
            payload.end_date,
        )

        season = Season(
            name=clean_name,
            description=clean_description,
            start_date=payload.start_date,
            end_date=payload.end_date,
            is_active=True,
        )

        db.add(season)

        db.flush()

        MarketingNotificationService.schedule_season(
            db,
            season=season,
        )

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="CREATE_SEASON",
            module="CATALOG",
            entity_type="Season",
            entity_id=season.id,
            description=(
                f"Se creó la temporada "
                f"'{season.name}'."
            ),
            old_values=None,
            new_values={
                "name": season.name,
                "description": season.description,
                "start_date": (
                    season.start_date.isoformat()
                    if season.start_date
                    else None
                ),
                "end_date": (
                    season.end_date.isoformat()
                    if season.end_date
                    else None
                ),
                "is_active": season.is_active,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        db.refresh(season)

        return season

    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_season(
        db: Session,
        season_id: int,
        payload: SeasonUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Season:

        season = SeasonService.get_season(
            db=db,
            season_id=season_id,
        )

        old_values = {
            "name": season.name,
            "description": season.description,
            "start_date": (
                season.start_date.isoformat()
                if season.start_date
                else None
            ),
            "end_date": (
                season.end_date.isoformat()
                if season.end_date
                else None
            ),
            "is_active": season.is_active,
        }

        update_data = payload.model_dump(
            exclude_unset=True
        )

        if (
            "name" in update_data
            and update_data["name"] is not None
        ):
            clean_name = (
                update_data["name"].strip()
            )

            SeasonService._validate_unique_name(
                db=db,
                name=clean_name,
                exclude_id=season.id,
            )

            season.name = clean_name

        if "description" in update_data:
            description = (
                update_data["description"]
            )

            season.description = (
                description.strip()
                if description
                else None
            )

        if "start_date" in update_data:
            season.start_date = (
                update_data["start_date"]
            )

        if "end_date" in update_data:
            season.end_date = (
                update_data["end_date"]
            )

        if (
            "is_active" in update_data
            and update_data["is_active"]
            is not None
        ):
            season.is_active = (
                update_data["is_active"]
            )

        SeasonService._validate_dates(
            season.start_date,
            season.end_date,
        )

        db.flush()

        MarketingNotificationService.schedule_season(
            db,
            season=season,
        )

        new_values = {
            "name": season.name,
            "description": season.description,
            "start_date": (
                season.start_date.isoformat()
                if season.start_date
                else None
            ),
            "end_date": (
                season.end_date.isoformat()
                if season.end_date
                else None
            ),
            "is_active": season.is_active,
        }

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="UPDATE_SEASON",
            module="CATALOG",
            entity_type="Season",
            entity_id=season.id,
            description=(
                f"Se actualizó la temporada "
                f"'{season.name}'."
            ),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        db.refresh(season)

        return season

    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_season(
        db: Session,
        season_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Season:

        season = SeasonService.get_season(
            db=db,
            season_id=season_id,
        )

        if not season.is_active:
            raise ValueError(
                "La temporada ya se encuentra inactiva."
            )

        season.is_active = False

        db.flush()

        MarketingNotificationService.cancel_pending_for_entity(
            db,
            campaign_type="SEASON",
            entity_id=season.id,
        )

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="DEACTIVATE_SEASON",
            module="CATALOG",
            entity_type="Season",
            entity_id=season.id,
            description=(
                f"Se desactivó la temporada "
                f"'{season.name}'."
            ),
            old_values={
                "is_active": True,
            },
            new_values={
                "is_active": False,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        db.refresh(season)

        return season