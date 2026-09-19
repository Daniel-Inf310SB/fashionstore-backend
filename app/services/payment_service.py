from __future__ import annotations

import math
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, aliased, joinedload

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.order import Order
from app.models.payment import Payment
from app.models.sale import Sale
from app.models.user import User
from app.services.order_service import OrderService
from app.services.notification_service import NotificationService
from app.services.receipt_service import ReceiptService
from app.services.stripe_service import StripeGateway


class PaymentService:
    ADMIN_ROLE = "ADMINISTRADOR"
    CUSTOMER_ROLE = "CLIENTE"
    ELECTRONIC_METHODS = ("CARD", "QR", "TRANSFER")
    CANCELLABLE_STATUSES = ("PENDING", "PROCESSING")

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(value or 0).quantize(Decimal("0.01"))

    @staticmethod
    def _role_name(user: User) -> str | None:
        return user.role.name if user.role is not None else None

    @staticmethod
    def _assert_admin(current_user: User) -> None:
        if PaymentService._role_name(current_user) != PaymentService.ADMIN_ROLE:
            raise PermissionError(
                "Solo el administrador puede acceder a la gestión global de pagos."
            )

    @staticmethod
    def _base_query(db: Session):
        return (
            db.query(Payment)
            .options(
                joinedload(Payment.user),
                joinedload(Payment.order).joinedload(Order.customer),
                joinedload(Payment.order).joinedload(Order.branch),
                joinedload(Payment.sale).joinedload(Sale.customer),
                joinedload(Payment.sale).joinedload(Sale.branch),
                joinedload(Payment.sale).joinedload(Sale.cashier),
            )
            .filter(Payment.payment_method.in_(PaymentService.ELECTRONIC_METHODS))
        )

    @staticmethod
    def _get_payment(db: Session, payment_id: int) -> Payment:
        payment = PaymentService._base_query(db).filter(Payment.id == payment_id).first()
        if payment is None:
            raise LookupError("El pago electrónico no existe.")
        return payment

    @staticmethod
    def _validate_payment_access(*, payment: Payment, current_user: User) -> None:
        role = PaymentService._role_name(current_user)
        if role == PaymentService.ADMIN_ROLE:
            return
        if role == PaymentService.CUSTOMER_ROLE:
            if payment.order is None or payment.order.customer_id != current_user.id:
                raise PermissionError("No puedes consultar el pago de otro cliente.")
            return
        raise PermissionError("Tu rol no puede consultar este pago electrónico.")

    @staticmethod
    def _source_data(payment: Payment):
        if payment.order is not None:
            return {
                "source_type": "ORDER",
                "source_code": payment.order.order_code,
                "customer": payment.order.customer,
                "branch": payment.order.branch,
                "order": payment.order,
                "sale": None,
            }
        if payment.sale is not None:
            return {
                "source_type": "SALE",
                "source_code": payment.sale.sale_code,
                "customer": payment.sale.customer,
                "branch": payment.sale.branch,
                "order": None,
                "sale": payment.sale,
            }
        raise ValueError("El pago no está relacionado con una compra ni con una venta.")

    @staticmethod
    def _serialize(payment: Payment) -> dict:
        source = PaymentService._source_data(payment)
        return {
            "id": payment.id,
            "payment_code": payment.payment_code,
            "order_id": payment.order_id,
            "sale_id": payment.sale_id,
            "user_id": payment.user_id,
            "source_type": source["source_type"],
            "source_code": source["source_code"],
            "payment_method": payment.payment_method,
            "channel": payment.channel,
            "provider": payment.provider,
            "amount": PaymentService._money(payment.amount),
            "currency": payment.currency,
            "status": payment.status,
            "external_transaction_id": payment.external_transaction_id,
            "external_reference": payment.external_reference,
            "failure_reason": payment.failure_reason,
            "paid_at": payment.paid_at,
            "created_at": payment.created_at,
            "updated_at": payment.updated_at,
            "customer": source["customer"],
            "branch": source["branch"],
            "order": source["order"],
            "sale": source["sale"],
        }

    @staticmethod
    def _serialize_status(payment: Payment) -> dict:
        source = PaymentService._source_data(payment)
        return {
            "id": payment.id,
            "payment_code": payment.payment_code,
            "source_type": source["source_type"],
            "source_code": source["source_code"],
            "status": payment.status,
            "payment_method": payment.payment_method,
            "amount": PaymentService._money(payment.amount),
            "currency": payment.currency,
            "provider": payment.provider,
            "external_transaction_id": payment.external_transaction_id,
            "failure_reason": payment.failure_reason,
            "paid_at": payment.paid_at,
            "updated_at": payment.updated_at,
        }

    @staticmethod
    def _audit(
        db: Session,
        *,
        current_user: User | None,
        payment: Payment,
        action: str,
        description: str,
        old_status: str | None = None,
    ) -> None:
        db.add(
            AuditLog(
                user_id=current_user.id if current_user is not None else payment.user_id,
                action=action,
                module="PAYMENTS",
                entity_type="Payment",
                entity_id=payment.id,
                description=description,
                old_values={"status": old_status} if old_status is not None else None,
                new_values={
                    "payment_code": payment.payment_code,
                    "status": payment.status,
                    "payment_method": payment.payment_method,
                    "amount": str(payment.amount),
                    "order_id": payment.order_id,
                    "sale_id": payment.sale_id,
                },
                status="SUCCESS",
            )
        )

    @staticmethod
    def _generate_payment_code() -> str:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d")
        return f"PAY-{stamp}-{uuid4().hex[:10].upper()}"

    @staticmethod
    def _retrieve_stripe_payment_intent(payment_intent_id: str):
        """Recupera un PaymentIntent ya creado sin generar otro intento."""
        return StripeGateway.retrieve_payment_intent(payment_intent_id)

    @staticmethod
    def _cancel_other_active_attempts(
        db: Session,
        *,
        approved_payment: Payment,
    ) -> None:
        """Cancela en Stripe los otros intentos activos de la misma compra.

        Solo cambia a CANCELLED los intentos cuya cancelación en Stripe
        realmente pudo completarse. Si Stripe no permite cancelarlo,
        se conserva su estado local para no ocultar una inconsistencia.
        """
        if approved_payment.order_id is None:
            return

        other_attempts = (
            db.query(Payment)
            .filter(
                Payment.order_id == approved_payment.order_id,
                Payment.id != approved_payment.id,
                Payment.provider == "STRIPE",
                Payment.status.in_(PaymentService.CANCELLABLE_STATUSES),
            )
            .all()
        )

        for other in other_attempts:
            cancelled = False

            if other.external_transaction_id:
                try:
                    StripeGateway.cancel_payment_intent(
                        other.external_transaction_id
                    )
                    cancelled = True
                except Exception as exc:
                    other.failure_reason = (
                        "No se pudo cancelar automáticamente el intento "
                        f"obsoleto después de aprobar otro pago: {exc}"
                    )[:2000]
            else:
                cancelled = True

            if cancelled:
                old_status = other.status
                other.status = "CANCELLED"
                other.failure_reason = (
                    "Intento cancelado automáticamente porque otro pago "
                    "de la misma compra fue aprobado."
                )
                PaymentService._audit(
                    db,
                    current_user=None,
                    payment=other,
                    action="AUTO_CANCEL",
                    description=(
                        f"Intento {other.payment_code} cancelado porque "
                        f"{approved_payment.payment_code} fue aprobado."
                    ),
                    old_status=old_status,
                )

    # =====================================================
    # MÉTODOS DISPONIBLES PARA CHECKOUT
    # =====================================================

    @staticmethod
    def list_payment_methods() -> dict:
        return {
            "items": [
                {
                    "code": "CARD",
                    "name": "Tarjeta de crédito/débito",
                    "provider": "STRIPE",
                    "enabled": bool(
                        settings.stripe_publishable_key and settings.stripe_secret_key
                    ),
                    "description": "Pago electrónico procesado por Stripe.",
                }
            ]
        }

    # =====================================================
    # CU38 - CREAR INTENTO STRIPE DESDE UNA COMPRA
    # =====================================================

    @staticmethod
    def create_stripe_payment_intent(
        db: Session,
        *,
        current_user: User,
        order_id: int,
    ) -> dict:
        if PaymentService._role_name(current_user) != PaymentService.CUSTOMER_ROLE:
            raise PermissionError("Solo el cliente puede iniciar el pago de su compra.")

        # Bloqueamos la orden para serializar dos clics/peticiones concurrentes
        # sobre la misma compra. Así evitamos crear dos PaymentIntent activos.
        order = (
            db.query(Order)
            .filter(Order.id == order_id)
            .with_for_update()
            .first()
        )

        if order is None:
            raise LookupError("La compra digital no existe.")

        if order.customer_id != current_user.id:
            raise PermissionError("No puedes pagar la compra de otro cliente.")

        if order.status not in {"PENDING_PAYMENT", "PAYMENT_FAILED"}:
            raise ValueError(
                f"La compra está en estado {order.status} y no admite un nuevo pago."
            )

        if settings.stripe_currency.upper() != "BOB":
            raise ValueError(
                "FashionStore calcula las compras en BOB. No se puede cambiar "
                "STRIPE_CURRENCY sin implementar una conversión monetaria explícita."
            )

        # Si ya existe un pago aprobado, nunca se inicia otro cobro.
        approved = (
            db.query(Payment)
            .filter(
                Payment.order_id == order.id,
                Payment.provider == "STRIPE",
                Payment.status == "APPROVED",
            )
            .first()
        )

        if approved is not None:
            raise ValueError("La compra ya tiene un pago aprobado.")

        # Regla principal:
        # una compra puede tener varios intentos históricos,
        # pero SOLO un intento activo (PENDING/PROCESSING) a la vez.
        active_payment = (
            db.query(Payment)
            .filter(
                Payment.order_id == order.id,
                Payment.provider == "STRIPE",
                Payment.status.in_(PaymentService.CANCELLABLE_STATUSES),
            )
            .order_by(Payment.id.desc())
            .first()
        )

        if active_payment is not None:
            if not active_payment.external_transaction_id:
                raise ValueError(
                    "Existe un intento de pago activo incompleto. "
                    "Cancélalo antes de iniciar otro."
                )

            try:
                intent = PaymentService._retrieve_stripe_payment_intent(
                    active_payment.external_transaction_id
                )
            except Exception as exc:
                raise ValueError(
                    "Existe un intento de pago activo, pero no se pudo "
                    f"recuperar desde Stripe: {exc}"
                ) from exc

            stripe_status = getattr(intent, "status", None)

            # Si Stripe ya lo canceló, sincronizamos localmente y permitimos
            # que el flujo continúe para crear un nuevo intento.
            if stripe_status == "canceled":
                old_status = active_payment.status
                active_payment.status = "CANCELLED"
                active_payment.failure_reason = (
                    "Stripe informó que el PaymentIntent estaba cancelado."
                )
                PaymentService._audit(
                    db,
                    current_user=current_user,
                    payment=active_payment,
                    action="SYNC_STATUS",
                    description=(
                        f"Stripe informó que {active_payment.payment_code} "
                        "estaba cancelado."
                    ),
                    old_status=old_status,
                )
                db.flush()

            # Si Stripe ya lo completó, NO generamos otro cobro.
            elif stripe_status == "succeeded":
                raise ValueError(
                    "Stripe ya confirmó este pago. "
                    "Espera unos segundos mientras el webhook actualiza la compra."
                )

            # Para requires_payment_method, requires_confirmation,
            # requires_action, processing, etc., reutilizamos el MISMO
            # PaymentIntent y su client_secret.
            else:
                client_secret = getattr(intent, "client_secret", None)

                if not client_secret:
                    raise ValueError(
                        "El intento activo de Stripe no tiene client_secret disponible."
                    )

                # La orden puede venir de PAYMENT_FAILED por un webhook anterior,
                # pero si el mismo PaymentIntent sigue reutilizable, la devolvemos
                # a pendiente mientras el cliente continúa el pago.
                order.status = "PENDING_PAYMENT"
                active_payment.status = "PROCESSING"
                db.commit()

                existing = PaymentService._get_payment(
                    db,
                    active_payment.id,
                )

                return {
                    "payment": PaymentService._serialize(existing),
                    "client_secret": client_secret,
                    "publishable_key": settings.stripe_publishable_key,
                    "reused": True,
                }

        # No existe intento activo reutilizable: creamos uno nuevo.
        payment = Payment(
            payment_code=PaymentService._generate_payment_code(),
            order_id=order.id,
            sale_id=None,
            user_id=current_user.id,
            payment_method="CARD",
            channel="ONLINE",
            provider="STRIPE",
            amount=PaymentService._money(order.total_amount),
            currency=settings.stripe_currency.upper(),
            status="PENDING",
        )

        db.add(payment)
        db.flush()
        order.status = "PENDING_PAYMENT"

        try:
            intent = StripeGateway.create_payment_intent(
                amount=payment.amount,
                currency=payment.currency,
                payment_code=payment.payment_code,
                order_id=order.id,
                order_code=order.order_code,
                customer_email=order.customer.email if order.customer else None,
            )

            payment.external_transaction_id = intent.id
            payment.external_reference = intent.id
            payment.status = "PROCESSING"
            client_secret = intent.client_secret

            PaymentService._audit(
                db,
                current_user=current_user,
                payment=payment,
                action="CREATE",
                description=f"Intento Stripe creado para {order.order_code}.",
                old_status="PENDING",
            )

            db.commit()

        except Exception as exc:
            db.rollback()

            # Si Stripe falló al crear el PaymentIntent, registramos el fallo
            # para conservar trazabilidad y permitir un reintento real.
            failed = Payment(
                payment_code=PaymentService._generate_payment_code(),
                order_id=order_id,
                sale_id=None,
                user_id=current_user.id,
                payment_method="CARD",
                channel="ONLINE",
                provider="STRIPE",
                amount=PaymentService._money(order.total_amount),
                currency=settings.stripe_currency.upper(),
                status="FAILED",
                failure_reason=str(exc)[:2000],
            )

            db.add(failed)

            persistent_order = (
                db.query(Order)
                .filter(Order.id == order_id)
                .first()
            )

            if persistent_order is not None:
                previous_order_status = persistent_order.status
                persistent_order.status = "PAYMENT_FAILED"

                if previous_order_status != "PAYMENT_FAILED":
                    NotificationService.notify_order_status(
                        db,
                        order=persistent_order,
                        status="PAYMENT_FAILED",
                    )

            db.commit()

            raise ValueError(
                f"No se pudo iniciar el pago con Stripe: {exc}"
            ) from exc

        created = PaymentService._get_payment(db, payment.id)

        return {
            "payment": PaymentService._serialize(created),
            "client_secret": client_secret,
            "publishable_key": settings.stripe_publishable_key,
            "reused": False,
        }

    # =====================================================
    # CU38 / CU39 - LISTADO ADMINISTRATIVO
    # =====================================================

    @staticmethod
    def list_payments(
        db: Session,
        *,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        branch_id: int | None = None,
        customer_id: int | None = None,
        order_id: int | None = None,
        sale_id: int | None = None,
        source_type: str | None = None,
        payment_status: str | None = None,
        payment_method: str | None = None,
        channel: str | None = None,
        provider: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        min_amount: Decimal | None = None,
        max_amount: Decimal | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict:
        PaymentService._assert_admin(current_user)
        order_customer = aliased(User)
        sale_customer = aliased(User)
        query = (
            PaymentService._base_query(db)
            .outerjoin(Order, Payment.order_id == Order.id)
            .outerjoin(Sale, Payment.sale_id == Sale.id)
            .outerjoin(order_customer, Order.customer_id == order_customer.id)
            .outerjoin(sale_customer, Sale.customer_id == sale_customer.id)
        )

        if search:
            term = f"%{search.strip()}%"
            query = query.filter(
                or_(
                    Payment.payment_code.ilike(term),
                    Payment.external_transaction_id.ilike(term),
                    Payment.external_reference.ilike(term),
                    Payment.provider.ilike(term),
                    Order.order_code.ilike(term),
                    Sale.sale_code.ilike(term),
                    order_customer.first_name.ilike(term),
                    order_customer.last_name.ilike(term),
                    order_customer.email.ilike(term),
                    order_customer.document_number.ilike(term),
                    sale_customer.first_name.ilike(term),
                    sale_customer.last_name.ilike(term),
                    sale_customer.email.ilike(term),
                    sale_customer.document_number.ilike(term),
                    cast(Payment.id, String).ilike(term),
                )
            )
        if branch_id is not None:
            query = query.filter(or_(Order.branch_id == branch_id, Sale.branch_id == branch_id))
        if customer_id is not None:
            query = query.filter(
                or_(Order.customer_id == customer_id, Sale.customer_id == customer_id)
            )
        if order_id is not None:
            query = query.filter(Payment.order_id == order_id)
        if sale_id is not None:
            query = query.filter(Payment.sale_id == sale_id)
        if source_type == "ORDER":
            query = query.filter(Payment.order_id.is_not(None))
        elif source_type == "SALE":
            query = query.filter(Payment.sale_id.is_not(None))
        if payment_status is not None:
            query = query.filter(Payment.status == payment_status)
        if payment_method is not None:
            query = query.filter(Payment.payment_method == payment_method)
        if channel is not None:
            query = query.filter(Payment.channel == channel)
        if provider:
            query = query.filter(Payment.provider.ilike(f"%{provider.strip()}%"))
        if date_from is not None:
            query = query.filter(Payment.created_at >= date_from)
        if date_to is not None:
            query = query.filter(Payment.created_at <= date_to)
        if min_amount is not None:
            query = query.filter(Payment.amount >= min_amount)
        if max_amount is not None:
            query = query.filter(Payment.amount <= max_amount)

        total = query.count()
        sort_columns = {
            "created_at": Payment.created_at,
            "updated_at": Payment.updated_at,
            "amount": Payment.amount,
            "payment_code": Payment.payment_code,
            "status": Payment.status,
            "payment_method": Payment.payment_method,
        }
        sort_column = sort_columns.get(sort_by, Payment.created_at)
        query = query.order_by(
            sort_column.asc() if sort_order == "asc" else sort_column.desc(),
            Payment.id.desc(),
        )
        payments = query.offset((page - 1) * page_size).limit(page_size).all()
        return {
            "items": [PaymentService._serialize(payment) for payment in payments],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": math.ceil(total / page_size) if total > 0 else 0,
        }

    @staticmethod
    def list_my_payments(
        db: Session,
        *,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:
        if PaymentService._role_name(current_user) != PaymentService.CUSTOMER_ROLE:
            raise PermissionError("Esta consulta está disponible solo para clientes.")
        query = (
            PaymentService._base_query(db)
            .join(Order, Payment.order_id == Order.id)
            .filter(Order.customer_id == current_user.id)
        )
        total = query.count()
        payments = (
            query.order_by(Payment.created_at.desc(), Payment.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )
        return {
            "items": [PaymentService._serialize(payment) for payment in payments],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": math.ceil(total / page_size) if total > 0 else 0,
        }

    @staticmethod
    def get_payment(
        db: Session,
        *,
        current_user: User,
        payment_id: int,
    ) -> dict:
        payment = PaymentService._get_payment(db, payment_id)
        PaymentService._validate_payment_access(payment=payment, current_user=current_user)
        return PaymentService._serialize(payment)

    @staticmethod
    def get_payment_status(
        db: Session,
        *,
        current_user: User,
        payment_id: int,
    ) -> dict:
        payment = PaymentService._get_payment(db, payment_id)
        PaymentService._validate_payment_access(payment=payment, current_user=current_user)
        return PaymentService._serialize_status(payment)

    @staticmethod
    def cancel_payment(
        db: Session,
        *,
        current_user: User,
        payment_id: int,
        reason: str,
    ) -> dict:
        PaymentService._assert_admin(current_user)
        payment = (
            db.query(Payment)
            .filter(
                Payment.id == payment_id,
                Payment.payment_method.in_(PaymentService.ELECTRONIC_METHODS),
            )
            .with_for_update()
            .first()
        )
        if payment is None:
            raise LookupError("El pago electrónico no existe.")
        if payment.status not in PaymentService.CANCELLABLE_STATUSES:
            raise ValueError("Solo se pueden cancelar pagos PENDING o PROCESSING.")

        if payment.provider == "STRIPE" and payment.external_transaction_id:
            StripeGateway.cancel_payment_intent(payment.external_transaction_id)

        old_status = payment.status
        payment.status = "CANCELLED"
        payment.failure_reason = reason.strip()
        PaymentService._audit(
            db,
            current_user=current_user,
            payment=payment,
            action="CANCEL",
            description=f"Intento {payment.payment_code} cancelado. Motivo: {reason.strip()}",
            old_status=old_status,
        )
        try:
            db.commit()
        except Exception:
            db.rollback()
            raise
        return PaymentService._serialize(PaymentService._get_payment(db, payment.id))

    # =====================================================
    # WEBHOOK STRIPE - FUENTE DE VERDAD DEL ESTADO DEL PAGO
    # =====================================================

    @staticmethod
    def process_stripe_webhook(
        db: Session,
        *,
        payload: bytes,
        signature: str,
    ) -> dict:
        try:
            event = StripeGateway.construct_webhook_event(payload, signature)
        except Exception as exc:
            raise ValueError(f"Webhook de Stripe inválido: {exc}") from exc

        event_type = event["type"]

        # Solo procesamos eventos cuyo objeto principal es un PaymentIntent.
        # Eventos como charge.succeeded o charge.updated también llegan al
        # webhook, pero no deben buscarse por external_transaction_id porque
        # allí guardamos el id "pi_..." del PaymentIntent.
        allowed_events = {
            "payment_intent.succeeded",
            "payment_intent.processing",
            "payment_intent.payment_failed",
            "payment_intent.canceled",
        }

        if event_type not in allowed_events:
            return {
                "received": True,
                "event_type": event_type,
                "ignored": True,
            }

        stripe_object = event["data"]["object"]

        # stripe-python devuelve StripeObject/PaymentIntent, no siempre dict.
        # Convertimos explícitamente para poder usar .get() con seguridad.
        if hasattr(stripe_object, "to_dict"):
            obj = stripe_object.to_dict()
        else:
            obj = dict(stripe_object)

        intent_id = obj.get("id")
        if not intent_id:
            return {
                "received": True,
                "event_type": event_type,
                "ignored": True,
            }

        # Primero bloqueamos SOLO la fila de payments.
        # Evitamos joinedload + FOR UPDATE para no generar LEFT OUTER JOIN
        # bloqueados, combinación que PostgreSQL rechaza.
        payment = (
            db.query(Payment)
            .filter(
                Payment.provider == "STRIPE",
                Payment.external_transaction_id == intent_id,
            )
            .with_for_update()
            .first()
        )
        if payment is None:
            return {"received": True, "event_type": event_type, "ignored": True}

        # Si el pago pertenece a una compra, bloqueamos también su Order
        # en una consulta independiente. Las relaciones/items se cargarán
        # normalmente al acceder a ellas dentro de la misma sesión.
        locked_order = None
        if payment.order_id is not None:
            locked_order = (
                db.query(Order)
                .filter(Order.id == payment.order_id)
                .with_for_update()
                .first()
            )

        old_status = payment.status
        order_became_payment_failed = False

        if event_type == "payment_intent.succeeded":
            payment.status = "APPROVED"
            payment.failure_reason = None
            payment.paid_at = datetime.now(timezone.utc)

            if locked_order is not None:
                OrderService.mark_paid_from_payment(
                    db,
                    order=locked_order,
                    payment=payment,
                )

                # Si quedaron intentos viejos PENDING/PROCESSING de pruebas
                # anteriores, intentamos cancelarlos en Stripe y cerrarlos
                # localmente. El pago aprobado nunca se toca.
                PaymentService._cancel_other_active_attempts(
                    db,
                    approved_payment=payment,
                )
        elif event_type == "payment_intent.processing":
            payment.status = "PROCESSING"
        elif event_type == "payment_intent.payment_failed":
            payment.status = "FAILED"
            last_error = obj.get("last_payment_error") or {}
            payment.failure_reason = (
                last_error.get("message") or "Stripe informó que el pago falló."
            )[:2000]
            if locked_order is not None and locked_order.status == "PENDING_PAYMENT":
                locked_order.status = "PAYMENT_FAILED"
                order_became_payment_failed = True
        elif event_type == "payment_intent.canceled":
            payment.status = "CANCELLED"
            payment.failure_reason = "PaymentIntent cancelado en Stripe."
            if locked_order is not None and locked_order.status == "PENDING_PAYMENT":
                locked_order.status = "PAYMENT_FAILED"
                order_became_payment_failed = True
        else:
            return {"received": True, "event_type": event_type, "ignored": True}

        if order_became_payment_failed and locked_order is not None:
            NotificationService.notify_order_status(
                db,
                order=locked_order,
                status="PAYMENT_FAILED",
            )

        if old_status != payment.status:
            PaymentService._audit(
                db,
                current_user=None,
                payment=payment,
                action="STRIPE_WEBHOOK",
                description=f"Stripe actualizó {payment.payment_code}: {old_status} -> {payment.status}.",
                old_status=old_status,
            )

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        # El pago ya esta confirmado y persistido. El correo/PDF se procesa
        # despues del commit para que un fallo externo de Brevo no revierta
        # una compra que Stripe ya aprobo. ReceiptService es idempotente:
        # reutiliza el comprobante de la orden y no reenvia si ya esta SENT.
        if event_type == "payment_intent.succeeded" and payment.order_id is not None:
            try:
                ReceiptService.issue_and_email_order_receipt(
                    db,
                    order_id=payment.order_id,
                    payment_id=payment.id,
                )
            except Exception:
                # El estado del comprobante queda FAILED cuando corresponde.
                # El webhook debe responder correctamente porque el pago ya
                # fue confirmado y no debe deshacerse por un error de email/PDF.
                pass

        return {"received": True, "event_type": event_type, "ignored": False}
