from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

from app.core.config import settings


class StripeGateway:
    @staticmethod
    def _stripe():
        try:
            import stripe
        except ImportError as exc:
            raise RuntimeError(
                "Falta instalar Stripe. Ejecuta: pip install stripe"
            ) from exc

        if not settings.stripe_secret_key:
            raise RuntimeError(
                "STRIPE_SECRET_KEY no está configurada en el archivo .env."
            )
        stripe.api_key = settings.stripe_secret_key
        return stripe

    @staticmethod
    def amount_to_minor_units(amount: Decimal) -> int:
        # BOB usa centavos. El importe nunca se toma del frontend; viene
        # del total persistido de la compra.
        normalized = Decimal(amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        return int(normalized * 100)

    @classmethod
    def create_payment_intent(
        cls,
        *,
        amount: Decimal,
        currency: str,
        payment_code: str,
        order_id: int,
        order_code: str,
        customer_email: str | None,
    ):
        stripe = cls._stripe()
        return stripe.PaymentIntent.create(
            amount=cls.amount_to_minor_units(amount),
            currency=currency.lower(),
            payment_method_types=["card"],
            receipt_email=customer_email or None,
            metadata={
                "payment_code": payment_code,
                "order_id": str(order_id),
                "order_code": order_code,
            },
            idempotency_key=f"fashionstore-{payment_code}",
        )

    @classmethod
    def retrieve_payment_intent(cls, payment_intent_id: str):
        stripe = cls._stripe()
        return stripe.PaymentIntent.retrieve(payment_intent_id)

    @classmethod
    def cancel_payment_intent(cls, payment_intent_id: str):
        stripe = cls._stripe()
        return stripe.PaymentIntent.cancel(payment_intent_id)

    @classmethod
    def construct_webhook_event(cls, payload: bytes, signature: str):
        stripe = cls._stripe()
        if not settings.stripe_webhook_secret:
            raise RuntimeError(
                "STRIPE_WEBHOOK_SECRET no está configurada en el archivo .env."
            )
        return stripe.Webhook.construct_event(
            payload=payload,
            sig_header=signature,
            secret=settings.stripe_webhook_secret,
        )
