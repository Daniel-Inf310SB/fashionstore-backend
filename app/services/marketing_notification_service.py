from __future__ import annotations

import logging
from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone,
)

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.collection import Collection
from app.models.notification_campaign import (
    NotificationCampaign,
)
from app.models.promotion import Promotion
from app.models.role import Role
from app.models.season import Season
from app.models.user import User
from app.services.notification_service import (
    NotificationService,
)


logger = logging.getLogger(__name__)


class MarketingNotificationService:

    @staticmethod
    def _utc_datetime(
        value: datetime | date | None,
    ) -> datetime:
        if value is None:
            return datetime.now(timezone.utc)

        if isinstance(value, datetime):
            if value.tzinfo is None:
                return value.replace(
                    tzinfo=timezone.utc
                )

            return value.astimezone(
                timezone.utc
            )

        return datetime.combine(
            value,
            time.min,
            tzinfo=timezone.utc,
        )

    @staticmethod
    def _upsert_campaign(
        db: Session,
        *,
        campaign_type: str,
        entity_id: int,
        event: str,
        title: str,
        message: str,
        action_url: str,
        scheduled_for: datetime,
        dedupe_key: str,
        enabled: bool,
    ) -> NotificationCampaign | None:
        campaign = (
            db.query(NotificationCampaign)
            .filter(
                NotificationCampaign.dedupe_key
                == dedupe_key
            )
            .first()
        )

        if campaign is None:
            if not enabled:
                print(
                    f"🚫 [MARKETING] Campaña no creada porque "
                    f"está deshabilitada | "
                    f"type={campaign_type} | "
                    f"entity_id={entity_id} | "
                    f"event={event}"
                )
                return None

            campaign = NotificationCampaign(
                campaign_type=campaign_type,
                entity_id=entity_id,
                event=event,
                title=title,
                message=message,
                action_url=action_url,
                target_type="ALL_CUSTOMERS",
                status="PENDING",
                scheduled_for=scheduled_for,
                attempt_count=0,
                dedupe_key=dedupe_key,
            )

            db.add(campaign)

            print(
                f"📅 [MARKETING] Campaña creada y programada | "
                f"type={campaign_type} | "
                f"entity_id={entity_id} | "
                f"event={event} | "
                f"scheduled_for={scheduled_for} | "
                f"dedupe_key={dedupe_key}"
            )

            return campaign

        # Si ya fue enviada no duplicamos una campaña
        # de lanzamiento por simples ediciones posteriores.
        if campaign.status == "COMPLETED":
            print(
                f"ℹ️ [MARKETING] Campaña ya completada; "
                f"no se vuelve a programar | "
                f"id={campaign.id} | "
                f"dedupe_key={dedupe_key}"
            )
            return campaign

        campaign.title = title
        campaign.message = message
        campaign.action_url = action_url
        campaign.scheduled_for = scheduled_for

        if enabled:
            campaign.status = "PENDING"
            campaign.last_error = None

            print(
                f"🔄 [MARKETING] Campaña actualizada/reprogramada | "
                f"id={campaign.id} | "
                f"scheduled_for={scheduled_for} | "
                f"status=PENDING"
            )
        else:
            campaign.status = "CANCELLED"

            print(
                f"🚫 [MARKETING] Campaña cancelada | "
                f"id={campaign.id} | "
                f"type={campaign_type} | "
                f"entity_id={entity_id}"
            )

        return campaign

    @staticmethod
    def schedule_promotion(
        db: Session,
        *,
        promotion: Promotion,
    ) -> NotificationCampaign | None:
        now = datetime.now(timezone.utc)

        start_at = (
            MarketingNotificationService
            ._utc_datetime(
                promotion.start_at
            )
        )

        end_at = (
            MarketingNotificationService
            ._utc_datetime(
                promotion.end_at
            )
        )

        enabled = bool(
            promotion.is_active
            and end_at > now
        )

        description = (
            promotion.description.strip()
            if promotion.description
            else (
                f"Descubre la promoción "
                f"{promotion.name}."
            )
        )

        return (
            MarketingNotificationService
            ._upsert_campaign(
                db,
                campaign_type="PROMOTION",
                entity_id=promotion.id,
                event="PROMOTION_LAUNCHED",
                title=(
                    f"Nueva promoción: "
                    f"{promotion.name}"
                ),
                message=description,
                action_url=(
                    f"/catalog?"
                    f"promotion_id={promotion.id}"
                ),
                scheduled_for=start_at,
                dedupe_key=(
                    f"PROMOTION:"
                    f"{promotion.id}:LAUNCH"
                ),
                enabled=enabled,
            )
        )

    @staticmethod
    def schedule_collection(
        db: Session,
        *,
        collection: Collection,
    ) -> NotificationCampaign | None:
        scheduled_for = (
            MarketingNotificationService
            ._utc_datetime(
                collection.launch_date
            )
        )

        description = (
            collection.description.strip()
            if collection.description
            else (
                f"Conoce la nueva colección "
                f"{collection.name}."
            )
        )

        return (
            MarketingNotificationService
            ._upsert_campaign(
                db,
                campaign_type="COLLECTION",
                entity_id=collection.id,
                event="COLLECTION_LAUNCHED",
                title=(
                    f"Nueva colección: "
                    f"{collection.name}"
                ),
                message=description,
                action_url=(
                    f"/catalog?"
                    f"collection_id={collection.id}"
                ),
                scheduled_for=scheduled_for,
                dedupe_key=(
                    f"COLLECTION:"
                    f"{collection.id}:LAUNCH"
                ),
                enabled=bool(
                    collection.is_active
                ),
            )
        )

    @staticmethod
    def schedule_season(
        db: Session,
        *,
        season: Season,
    ) -> NotificationCampaign | None:
        today = date.today()

        scheduled_for = (
            MarketingNotificationService
            ._utc_datetime(
                season.start_date
            )
        )

        enabled = bool(
            season.is_active
            and (
                season.end_date is None
                or season.end_date >= today
            )
        )

        description = (
            season.description.strip()
            if season.description
            else (
                f"Ya comenzó la temporada "
                f"{season.name}."
            )
        )

        return (
            MarketingNotificationService
            ._upsert_campaign(
                db,
                campaign_type="SEASON",
                entity_id=season.id,
                event="SEASON_STARTED",
                title=(
                    f"Temporada "
                    f"{season.name}"
                ),
                message=description,
                action_url=(
                    f"/catalog?"
                    f"season_id={season.id}"
                ),
                scheduled_for=scheduled_for,
                dedupe_key=(
                    f"SEASON:"
                    f"{season.id}:START"
                ),
                enabled=enabled,
            )
        )

    @staticmethod
    def cancel_pending_for_entity(
        db: Session,
        *,
        campaign_type: str,
        entity_id: int,
    ) -> int:
        campaigns = (
            db.query(NotificationCampaign)
            .filter(
                NotificationCampaign.campaign_type
                == campaign_type,

                NotificationCampaign.entity_id
                == entity_id,

                NotificationCampaign.status
                .in_(["PENDING", "FAILED"]),
            )
            .all()
        )

        for campaign in campaigns:
            campaign.status = "CANCELLED"

        return len(campaigns)

    @staticmethod
    def process_due_campaigns(
        db: Session,
        *,
        limit: int | None = None,
    ) -> dict:
        now = datetime.now(timezone.utc)

        campaign_limit = (
            limit
            or settings
            .marketing_campaign_batch_size
        )

        campaigns = (
            db.query(NotificationCampaign)
            .filter(
                NotificationCampaign.status
                == "PENDING",

                NotificationCampaign.scheduled_for
                <= now,
            )
            .order_by(
                NotificationCampaign
                .scheduled_for.asc(),

                NotificationCampaign.id.asc(),
            )
            .limit(campaign_limit)
            .all()
        )

        print(
            f"🔎 [MARKETING] Buscando campañas pendientes | "
            f"now={now.isoformat()} | "
            f"encontradas={len(campaigns)} | "
            f"limit={campaign_limit}"
        )

        result = {
            "processed_campaigns": 0,
            "completed_campaigns": 0,
            "failed_campaigns": 0,
            "notifications_created": 0,
        }

        for campaign in campaigns:
            result["processed_campaigns"] += 1

            campaign_notifications = 0

            print(
                f"🚀 [MARKETING] Iniciando campaña | "
                f"id={campaign.id} | "
                f"type={campaign.campaign_type} | "
                f"event={campaign.event} | "
                f"entity_id={campaign.entity_id} | "
                f"scheduled_for={campaign.scheduled_for} | "
                f"title={campaign.title!r}"
            )

            try:
                campaign.status = "PROCESSING"
                campaign.started_at = now
                campaign.attempt_count += 1
                campaign.last_error = None
                db.commit()

                print(
                    f"⚙️ [MARKETING] Campaña {campaign.id} "
                    f"marcada como PROCESSING | "
                    f"intento={campaign.attempt_count}"
                )

                last_user_id = 0

                while True:
                    customers = (
                        db.query(User)
                        .join(Role)
                        .filter(
                            User.id > last_user_id,
                            User.is_active.is_(True),
                            Role.is_active.is_(True),
                            Role.name == "CLIENTE",
                        )
                        .order_by(User.id.asc())
                        .limit(
                            settings
                            .marketing_customer_batch_size
                        )
                        .all()
                    )

                    if not customers:
                        print(
                            f"📭 [MARKETING] No hay más clientes "
                            f"para campaña {campaign.id}."
                        )
                        break

                    print(
                        f"👥 [MARKETING] Procesando lote | "
                        f"campaign={campaign.id} | "
                        f"clientes={len(customers)} | "
                        f"desde_user_id>{last_user_id}"
                    )

                    for customer in customers:
                        print(
                            f"➡️ [MARKETING] Creando notificación | "
                            f"campaign={campaign.id} | "
                            f"user_id={customer.id} | "
                            f"email={customer.email}"
                        )

                        created = (
                            NotificationService.create(
                                db,
                                user_id=customer.id,
                                notification_type="SYSTEM",
                                event=campaign.event,
                                title=campaign.title,
                                message=campaign.message,
                                entity_type=(
                                    campaign.campaign_type
                                ),
                                entity_id=(
                                    campaign.entity_id
                                ),
                                action_url=(
                                    campaign.action_url
                                ),
                                dedupe_key=(
                                    f"CAMPAIGN:"
                                    f"{campaign.id}:"
                                    f"USER:{customer.id}"
                                ),
                            )
                        )

                        if created is not None:
                            result[
                                "notifications_created"
                            ] += 1

                            campaign_notifications += 1

                            print(
                                f"📨 [MARKETING] Notificación creada | "
                                f"campaign={campaign.id} | "
                                f"user_id={customer.id} | "
                                f"notification_id="
                                f"{getattr(created, 'id', None)}"
                            )
                        else:
                            print(
                                f"⏭️ [MARKETING] Notificación omitida "
                                f"o duplicada | "
                                f"campaign={campaign.id} | "
                                f"user_id={customer.id}"
                            )

                    db.commit()

                    print(
                        f"💾 [MARKETING] Lote confirmado | "
                        f"campaign={campaign.id} | "
                        f"ultimo_user_id={customers[-1].id}"
                    )

                    last_user_id = (
                        customers[-1].id
                    )

                campaign = db.get(
                    NotificationCampaign,
                    campaign.id,
                )

                if campaign is None:
                    raise RuntimeError(
                        "La campaña desapareció durante "
                        "el procesamiento."
                    )

                campaign.status = "COMPLETED"
                campaign.completed_at = (
                    datetime.now(timezone.utc)
                )
                campaign.last_error = None

                db.commit()

                result[
                    "completed_campaigns"
                ] += 1

                print(
                    f"✅ [MARKETING] Campaña completada | "
                    f"id={campaign.id} | "
                    f"notificaciones_creadas="
                    f"{campaign_notifications} | "
                    f"completed_at="
                    f"{campaign.completed_at}"
                )

            except Exception as error:
                db.rollback()

                print(
                    f"❌ [MARKETING] Error procesando campaña | "
                    f"id={campaign.id} | "
                    f"error={error}"
                )

                logger.exception(
                    "Error procesando campaña id=%s",
                    campaign.id,
                )

                failed_campaign = db.get(
                    NotificationCampaign,
                    campaign.id,
                )

                if failed_campaign is None:
                    print(
                        f"⚠️ [MARKETING] No se pudo recuperar "
                        f"la campaña {campaign.id} tras el error."
                    )
                    continue

                failed_campaign.last_error = (
                    str(error)[:2000]
                )

                if (
                    failed_campaign.attempt_count
                    >= settings
                    .marketing_campaign_max_retries
                ):
                    failed_campaign.status = "FAILED"

                    print(
                        f"🛑 [MARKETING] Campaña marcada FAILED | "
                        f"id={failed_campaign.id} | "
                        f"intentos="
                        f"{failed_campaign.attempt_count}"
                    )
                else:
                    failed_campaign.status = "PENDING"
                    failed_campaign.scheduled_for = (
                        datetime.now(timezone.utc)
                        + timedelta(
                            minutes=(
                                settings
                                .marketing_campaign_retry_minutes
                            )
                        )
                    )

                    print(
                        f"🔁 [MARKETING] Campaña reprogramada | "
                        f"id={failed_campaign.id} | "
                        f"nuevo_scheduled_for="
                        f"{failed_campaign.scheduled_for}"
                    )

                db.commit()

                result[
                    "failed_campaigns"
                ] += 1

        print(
            f"🏁 [MARKETING] Fin del procesamiento | "
            f"resultado={result}"
        )

        return result

