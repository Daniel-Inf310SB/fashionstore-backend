from __future__ import annotations

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session

from app.models.product_promotion import ProductPromotion
from app.models.promotion import Promotion


class CustomerPricingService:
    MONEY = Decimal('0.01')

    @staticmethod
    def apply_discount(price: Decimal, promotion: Promotion | None) -> Decimal:
        price = Decimal(price)
        if promotion is None:
            return price.quantize(CustomerPricingService.MONEY, rounding=ROUND_HALF_UP)

        value = Decimal(promotion.discount_value or 0)
        discount_type = str(promotion.discount_type or '').upper()

        if discount_type == 'PERCENTAGE':
            final_price = price * (Decimal('1') - (value / Decimal('100')))
        elif discount_type == 'FIXED':
            final_price = price - value
        else:
            final_price = price

        if final_price < Decimal('0'):
            final_price = Decimal('0')

        return final_price.quantize(CustomerPricingService.MONEY, rounding=ROUND_HALF_UP)

    @staticmethod
    def get_active_promotions_by_product(
        db: Session,
        product_ids: list[int],
    ) -> dict[int, list[Promotion]]:
        if not product_ids:
            return {}

        now = datetime.now(timezone.utc)
        rows = (
            db.query(ProductPromotion.product_id, Promotion)
            .join(Promotion, ProductPromotion.promotion_id == Promotion.id)
            .filter(
                ProductPromotion.product_id.in_(product_ids),
                Promotion.is_active.is_(True),
                Promotion.start_at <= now,
                Promotion.end_at >= now,
            )
            .all()
        )

        result: dict[int, list[Promotion]] = {}
        for product_id, promotion in rows:
            result.setdefault(product_id, []).append(promotion)
        return result

    @staticmethod
    def choose_best_promotion(
        promotions: list[Promotion] | None,
        reference_price: Decimal,
    ) -> Promotion | None:
        if not promotions:
            return None

        reference_price = Decimal(reference_price)
        return min(
            promotions,
            key=lambda promotion: CustomerPricingService.apply_discount(reference_price, promotion),
        )

    @staticmethod
    def promotion_payload(promotion: Promotion | None) -> dict | None:
        if promotion is None:
            return None
        return {
            'id': promotion.id,
            'name': promotion.name,
            'discount_type': promotion.discount_type,
            'discount_value': promotion.discount_value,
        }
