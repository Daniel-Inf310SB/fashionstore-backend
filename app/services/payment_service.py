from __future__ import annotations

import math

from datetime import datetime
from decimal import Decimal

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, aliased, joinedload

from app.models.audit_log import AuditLog
from app.models.order import Order
from app.models.payment import Payment
from app.models.sale import Sale
from app.models.user import User


class PaymentService:
    """
    Módulo 11 orientado al panel administrativo.

    Los endpoints de este servicio trabajan únicamente con pagos
    electrónicos (CARD, QR y TRANSFER). Los pagos CASH pertenecen al flujo
    de caja/ventas presenciales y no se mezclan en esta vista.
    """

    ADMIN_ROLE = "ADMINISTRADOR"
    ELECTRONIC_METHODS = ("CARD", "QR", "TRANSFER")
    CANCELLABLE_STATUSES = ("PENDING", "PROCESSING")

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(value or 0).quantize(Decimal("0.01"))

    @staticmethod
    def _assert_admin(current_user: User) -> None:
        role_name = (
            current_user.role.name
            if current_user.role is not None
            else None
        )

        if role_name != PaymentService.ADMIN_ROLE:
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
            .filter(
                Payment.payment_method.in_(
                    PaymentService.ELECTRONIC_METHODS
                )
            )
        )

    @staticmethod
    def _get_payment(
        db: Session,
        payment_id: int,
    ) -> Payment:
        payment = (
            PaymentService._base_query(db)
            .filter(Payment.id == payment_id)
            .first()
        )

        if payment is None:
            raise LookupError(
                "El pago electrónico no existe."
            )

        return payment

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

        # La constraint de BD debería impedirlo, pero mantenemos una
        # validación defensiva para no devolver respuestas incoherentes.
        raise ValueError(
            "El pago no está relacionado con una compra ni con una venta."
        )

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
        current_user: User,
        payment: Payment,
        action: str,
        description: str,
        old_status: str | None = None,
    ) -> None:
        db.add(
            AuditLog(
                user_id=current_user.id,
                action=action,
                module="PAYMENTS",
                entity_type="Payment",
                entity_id=payment.id,
                description=description,
                old_values=(
                    {"status": old_status}
                    if old_status is not None
                    else None
                ),
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
            .outerjoin(
                order_customer,
                Order.customer_id == order_customer.id,
            )
            .outerjoin(
                sale_customer,
                Sale.customer_id == sale_customer.id,
            )
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
            query = query.filter(
                or_(
                    Order.branch_id == branch_id,
                    Sale.branch_id == branch_id,
                )
            )

        if customer_id is not None:
            query = query.filter(
                or_(
                    Order.customer_id == customer_id,
                    Sale.customer_id == customer_id,
                )
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
            query = query.filter(
                Payment.provider.ilike(f"%{provider.strip()}%")
            )

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

        sort_column = sort_columns.get(
            sort_by,
            Payment.created_at,
        )

        query = query.order_by(
            sort_column.asc()
            if sort_order == "asc"
            else sort_column.desc(),
            Payment.id.desc(),
        )

        payments = (
            query
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": [
                PaymentService._serialize(payment)
                for payment in payments
            ],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (
                math.ceil(total / page_size)
                if total > 0
                else 0
            ),
        }

    # =====================================================
    # CU38 / CU39 - DETALLE
    # =====================================================

    @staticmethod
    def get_payment(
        db: Session,
        *,
        current_user: User,
        payment_id: int,
    ) -> dict:
        PaymentService._assert_admin(current_user)
        payment = PaymentService._get_payment(db, payment_id)
        return PaymentService._serialize(payment)

    # =====================================================
    # CU39 - CONSULTAR ESTADO
    # =====================================================

    @staticmethod
    def get_payment_status(
        db: Session,
        *,
        current_user: User,
        payment_id: int,
    ) -> dict:
        PaymentService._assert_admin(current_user)
        payment = PaymentService._get_payment(db, payment_id)
        return PaymentService._serialize_status(payment)

    # =====================================================
    # CU38 - CANCELAR INTENTO DE PAGO PENDIENTE
    # =====================================================

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
                Payment.payment_method.in_(
                    PaymentService.ELECTRONIC_METHODS
                ),
            )
            .with_for_update()
            .first()
        )

        if payment is None:
            raise LookupError(
                "El pago electrónico no existe."
            )

        if payment.status not in PaymentService.CANCELLABLE_STATUSES:
            raise ValueError(
                "Solo se pueden cancelar pagos en estado "
                "PENDING o PROCESSING."
            )

        old_status = payment.status
        payment.status = "CANCELLED"
        payment.failure_reason = reason.strip()

        # No alteramos Order/Sale: se cancela este intento de pago, no la
        # operación comercial. Así puede existir un nuevo intento válido.
        PaymentService._audit(
            db,
            current_user=current_user,
            payment=payment,
            action="CANCEL",
            description=(
                f"El administrador canceló el intento de pago "
                f"{payment.payment_code}. Motivo: {reason.strip()}"
            ),
            old_status=old_status,
        )

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        updated = PaymentService._get_payment(db, payment.id)
        return PaymentService._serialize(updated)
