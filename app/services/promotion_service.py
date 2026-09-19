import math

from datetime import datetime
from decimal import Decimal
from typing import Literal

from sqlalchemy import (
    func,
    or_,
)

from sqlalchemy.orm import Session

from app.models.promotion import Promotion

from app.schemas.promotion import (
    PromotionCreate,
    PromotionUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


from app.services.marketing_notification_service import MarketingNotificationService
class PromotionService:

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_promotions(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        is_active: bool | None = None,
        discount_type: str | None = None,
        start_from: datetime | None = None,
        end_to: datetime | None = None,
        sort_by: Literal[
            "id",
            "name",
            "discount_type",
            "discount_value",
            "start_at",
            "end_at",
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
            Promotion
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
                        Promotion.name.ilike(
                            pattern
                        ),
                        Promotion.description.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # ESTADO
        # =================================================

        if is_active is not None:

            query = query.filter(
                Promotion.is_active
                == is_active
            )

        # =================================================
        # TIPO DE DESCUENTO
        # =================================================

        if discount_type:

            clean_type = (
                discount_type
                .strip()
                .upper()
            )

            query = query.filter(
                Promotion.discount_type
                == clean_type
            )

        # =================================================
        # FECHA DESDE
        # =================================================

        if start_from is not None:

            query = query.filter(
                Promotion.start_at
                >= start_from
            )

        # =================================================
        # FECHA HASTA
        # =================================================

        if end_to is not None:

            query = query.filter(
                Promotion.end_at
                <= end_to
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
                Promotion.id,

            "name":
                Promotion.name,

            "discount_type":
                Promotion.discount_type,

            "discount_value":
                Promotion.discount_value,

            "start_at":
                Promotion.start_at,

            "end_at":
                Promotion.end_at,

            "is_active":
                Promotion.is_active,

            "created_at":
                Promotion.created_at,

            "updated_at":
                Promotion.updated_at,
        }

        sort_column = (
            sort_columns[
                sort_by
            ]
        )

        if sort_order == "desc":

            query = query.order_by(
                sort_column.desc(),
                Promotion.id.desc(),
            )

        else:

            query = query.order_by(
                sort_column.asc(),
                Promotion.id.asc(),
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
    def get_promotion(
        db: Session,
        promotion_id: int,
    ) -> Promotion:

        promotion = db.get(
            Promotion,
            promotion_id,
        )

        if promotion is None:

            raise LookupError(
                "Promoción no encontrada."
            )

        return promotion

    # =====================================================
    # VALIDAR DATOS
    # =====================================================

    @staticmethod
    def _validate_data(
        discount_type: str,
        discount_value: Decimal,
        start_at: datetime,
        end_at: datetime,
    ) -> None:

        clean_type = (
            discount_type
            .strip()
            .upper()
        )

        if clean_type not in {
            "PERCENTAGE",
            "FIXED",
        }:

            raise ValueError(
                "El tipo de descuento debe ser "
                "PERCENTAGE o FIXED."
            )

        if discount_value <= 0:

            raise ValueError(
                "El valor del descuento "
                "debe ser mayor a 0."
            )

        if (
            clean_type
            == "PERCENTAGE"
            and discount_value
            > Decimal("100")
        ):

            raise ValueError(
                "El descuento porcentual "
                "no puede ser mayor a 100."
            )

        if end_at <= start_at:

            raise ValueError(
                "La fecha final debe ser "
                "posterior a la fecha inicial."
            )

    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_promotion(
        db: Session,
        payload: PromotionCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Promotion:

        clean_name = (
            payload.name.strip()
        )

        clean_description = (
            payload.description.strip()
            if payload.description
            else None
        )

        clean_type = (
            payload.discount_type
            .strip()
            .upper()
        )

        PromotionService._validate_data(
            discount_type=
                clean_type,

            discount_value=
                payload.discount_value,

            start_at=
                payload.start_at,

            end_at=
                payload.end_at,
        )

        promotion = Promotion(
            name=
                clean_name,

            description=
                clean_description,

            discount_type=
                clean_type,

            discount_value=
                payload.discount_value,

            start_at=
                payload.start_at,

            end_at=
                payload.end_at,

            is_active=
                True,
        )

        db.add(
            promotion
        )

        db.flush()

        MarketingNotificationService.schedule_promotion(
            db,
            promotion=promotion,
        )

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "CREATE_PROMOTION",

            module=
                "CATALOG",

            entity_type=
                "Promotion",

            entity_id=
                promotion.id,

            description=(
                f"Se creó la promoción "
                f"'{promotion.name}'."
            ),

            old_values=
                None,

            new_values={
                "name":
                    promotion.name,

                "description":
                    promotion.description,

                "discount_type":
                    promotion.discount_type,

                "discount_value":
                    str(
                        promotion.discount_value
                    ),

                "start_at":
                    promotion.start_at
                    .isoformat(),

                "end_at":
                    promotion.end_at
                    .isoformat(),

                "is_active":
                    promotion.is_active,
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
            promotion
        )

        return promotion

    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_promotion(
        db: Session,
        promotion_id: int,
        payload: PromotionUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Promotion:

        promotion = (
            PromotionService
            .get_promotion(
                db=db,
                promotion_id=
                    promotion_id,
            )
        )

        old_values = {
            "name":
                promotion.name,

            "description":
                promotion.description,

            "discount_type":
                promotion.discount_type,

            "discount_value":
                str(
                    promotion.discount_value
                ),

            "start_at":
                promotion.start_at
                .isoformat(),

            "end_at":
                promotion.end_at
                .isoformat(),

            "is_active":
                promotion.is_active,
        }

        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )

        if (
            "name"
            in update_data
            and update_data[
                "name"
            ] is not None
        ):

            promotion.name = (
                update_data[
                    "name"
                ].strip()
            )

        if (
            "description"
            in update_data
        ):

            description = (
                update_data[
                    "description"
                ]
            )

            promotion.description = (
                description.strip()
                if description
                else None
            )

        if (
            "discount_type"
            in update_data
            and update_data[
                "discount_type"
            ] is not None
        ):

            promotion.discount_type = (
                update_data[
                    "discount_type"
                ]
                .strip()
                .upper()
            )

        if (
            "discount_value"
            in update_data
            and update_data[
                "discount_value"
            ] is not None
        ):

            promotion.discount_value = (
                update_data[
                    "discount_value"
                ]
            )

        if (
            "start_at"
            in update_data
            and update_data[
                "start_at"
            ] is not None
        ):

            promotion.start_at = (
                update_data[
                    "start_at"
                ]
            )

        if (
            "end_at"
            in update_data
            and update_data[
                "end_at"
            ] is not None
        ):

            promotion.end_at = (
                update_data[
                    "end_at"
                ]
            )

        if (
            "is_active"
            in update_data
            and update_data[
                "is_active"
            ] is not None
        ):

            promotion.is_active = (
                update_data[
                    "is_active"
                ]
            )

        # =================================================
        # VALIDAR ESTADO FINAL
        # =================================================

        PromotionService._validate_data(
            discount_type=
                promotion.discount_type,

            discount_value=
                promotion.discount_value,

            start_at=
                promotion.start_at,

            end_at=
                promotion.end_at,
        )

        db.flush()

        MarketingNotificationService.schedule_promotion(
            db,
            promotion=promotion,
        )

        new_values = {
            "name":
                promotion.name,

            "description":
                promotion.description,

            "discount_type":
                promotion.discount_type,

            "discount_value":
                str(
                    promotion.discount_value
                ),

            "start_at":
                promotion.start_at
                .isoformat(),

            "end_at":
                promotion.end_at
                .isoformat(),

            "is_active":
                promotion.is_active,
        }

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_PROMOTION",

            module=
                "CATALOG",

            entity_type=
                "Promotion",

            entity_id=
                promotion.id,

            description=(
                f"Se actualizó la promoción "
                f"'{promotion.name}'."
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
            promotion
        )

        return promotion

    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_promotion(
        db: Session,
        promotion_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Promotion:

        promotion = (
            PromotionService
            .get_promotion(
                db=db,
                promotion_id=
                    promotion_id,
            )
        )

        if not promotion.is_active:

            raise ValueError(
                "La promoción ya se encuentra inactiva."
            )

        promotion.is_active = False

        db.flush()

        MarketingNotificationService.cancel_pending_for_entity(
            db,
            campaign_type="PROMOTION",
            entity_id=promotion.id,
        )

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "DEACTIVATE_PROMOTION",

            module=
                "CATALOG",

            entity_type=
                "Promotion",

            entity_id=
                promotion.id,

            description=(
                f"Se desactivó la promoción "
                f"'{promotion.name}'."
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
            promotion
        )

        return promotion