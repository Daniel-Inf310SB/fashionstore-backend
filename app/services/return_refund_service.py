"""Refunds are explicit, test-mode-only and never modify stock or the order's PAID flag.

A PROCESSING refund with an unknown Stripe outcome must be reconciled, NOT blindly
reissued: Stripe's idempotency guarantees are not indefinite.
"""
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.core.config import settings
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.return_request import ReturnRequest
from app.models.return_refund import ReturnRefund
from app.models.post_sale_case import PostSaleCase, PostSaleSettlement
from app.services.return_service import ReturnService
from app.services.stripe_service import StripeGateway

CENT = Decimal('0.01')

class ReturnRefundService:
    @staticmethod
    def _check_admin(user):
        ReturnService._admin(user)
        return ReturnService._tenant(user)

    @staticmethod
    def _load(db, user, return_id, lock=False):
        tenant_id = ReturnRefundService._check_admin(user)
        q = select(ReturnRequest).where(ReturnRequest.id == return_id, ReturnRequest.tenant_id == tenant_id)
        if lock:
            q = q.with_for_update()
        ret = db.scalar(q)
        if ret is None:
            raise LookupError('Devolución no encontrada en tu empresa.')
        if ret.status != 'RECEIVED':
            raise ValueError('Solo se reembolsan devoluciones recibidas.')
        return ret

    @staticmethod
    def _amount_and_payment(db, ret):
        order = db.scalar(select(Order).where(Order.id == ret.order_id, Order.tenant_id == ret.tenant_id).with_for_update())
        if order is None or order.status not in {'PAID','PREPARING','READY_FOR_PICKUP','SHIPPED','DELIVERED','COMPLETED'}:
            raise ValueError('Pedido no elegible para reembolso.')
        payments = db.scalars(select(Payment).where(
            Payment.order_id == order.id,
            Payment.status == 'APPROVED',
            Payment.provider == 'STRIPE',
        ).with_for_update()).all()
        if not payments:
            raise ValueError(
                'Este pedido no tiene un cobro Stripe aprobado registrado. '
                'No se puede preparar un reembolso automático: comprueba el pago original '
                'y tramita el caso por el procedimiento de devolución manual autorizado.'
            )
        if len(payments) != 1:
            raise ValueError(
                'El pedido tiene múltiples cobros Stripe aprobados. '
                'Se requiere conciliación manual antes de reembolsar.'
            )
        if not payments[0].external_transaction_id or not payments[0].external_transaction_id.startswith('pi_'):
            raise ValueError(
                'El cobro aprobado no tiene un PaymentIntent de Stripe válido. '
                'Verifica el identificador original con Stripe antes de cualquier reembolso.'
            )
        payment = payments[0]
        if payment.currency.upper() != 'BOB' or payment.amount != order.total_amount:
            raise ValueError('El pago y el pedido no coinciden.')
        ordered = {i.id:i for i in db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()}
        if sum((i.subtotal for i in ordered.values()),Decimal('0')) != order.total_amount:
            raise ValueError('Los importes de líneas no concilian con lo pagado. Revisión manual.')
        amount = Decimal('0')
        for line in ret.items:
            item = ordered.get(line.order_item_id)
            if item is None or line.quantity > item.quantity:
                raise ValueError('Cantidad o línea inválida.')
            amount += (item.subtotal * Decimal(line.quantity) / Decimal(item.quantity)).quantize(CENT,rounding=ROUND_HALF_UP)
        amount = amount.quantize(CENT)
        if amount <= 0:
            raise ValueError('Importe no reembolsable.')
        # Serializar por pedido; incluir reembolsos en curso para evitar exceder el cobro.
        other = db.scalar(select(func.coalesce(func.sum(ReturnRefund.amount),0)).join(ReturnRequest, ReturnRequest.id == ReturnRefund.return_request_id).where(ReturnRequest.order_id == order.id, ReturnRefund.status.in_(['PREPARED','PROCESSING','SUCCEEDED','MANUAL_REVIEW']), ReturnRefund.return_request_id != ret.id))
        unified_other = db.scalar(
            select(func.coalesce(func.sum(PostSaleSettlement.amount), 0))
            .join(PostSaleCase, PostSaleCase.id == PostSaleSettlement.case_id)
            .where(
                PostSaleCase.order_id == order.id,
                PostSaleSettlement.kind == 'REFUND',
                PostSaleSettlement.status.in_(['PROCESSING', 'COMPLETED', 'MANUAL_REVIEW']),
            )
        )
        if Decimal(other) + Decimal(unified_other or 0) + amount > payment.amount:
            raise ValueError('Se supera el importe original pagado al considerar los reintegros anteriores.')
        return amount,payment

    @staticmethod
    def preview(db: Session,user,return_id: int):
        ret = ReturnRefundService._load(db,user,return_id)
        amount,payment = ReturnRefundService._amount_and_payment(db,ret)
        saved = db.scalar(select(ReturnRefund).where(ReturnRefund.return_request_id == ret.id))
        return {'return_request_id':ret.id, 'payment_id':payment.id, 'currency':payment.currency, 'amount':amount, 'status':saved.status if saved else 'NOT_STARTED', 'note':'Vista previa; no envía dinero ni modifica inventario.'}

    @staticmethod
    def prepare(db: Session,user,return_id: int):
        ReturnRefundService._check_admin(user)
        try:
            ret = ReturnRefundService._load(db,user,return_id,lock=True)
            saved = db.scalar(select(ReturnRefund).where(ReturnRefund.return_request_id == ret.id).with_for_update())
            if saved is not None:
                db.commit();return saved
            amount,payment = ReturnRefundService._amount_and_payment(db,ret)
            key = f'fashionstore-return-{ret.id}-payment-{payment.id}-v1'
            refund = ReturnRefund(return_request_id=ret.id,tenant_id=ret.tenant_id,payment_id=payment.id,requested_by=user.id,amount=amount,currency=payment.currency.upper(),status='PREPARED',idempotency_key=key)
            db.add(refund);db.commit();db.refresh(refund);return refund
        except Exception:
            db.rollback();raise

    @staticmethod
    def execute(db: Session,user,return_id: int):
        ReturnRefundService._check_admin(user)
        # Gate: never permit real-world transfers from this provisional module.
        if not settings.stripe_secret_key.startswith('sk_test_'):
            raise PermissionError('Reembolsos habilitados solo con STRIPE_SECRET_KEY de pruebas (sk_test_).')
        try:
            ret = ReturnRefundService._load(db,user,return_id,lock=True)
            refund = db.scalar(select(ReturnRefund).where(ReturnRefund.return_request_id == ret.id).with_for_update())
            if refund is None:
                raise ValueError('Primero prepara el reembolso.')
            if refund.status != 'PREPARED':
                raise ValueError('Operación ya iniciada o finalizada. Consultar/conciliar, no repetir.')
            amount,payment = ReturnRefundService._amount_and_payment(db,ret)
            if amount != refund.amount or payment.id != refund.payment_id:
                raise ValueError('El importe o el pago original cambió.')
            intent_id = payment.external_transaction_id
            refund.status='PROCESSING';db.commit()
        except Exception:
            db.rollback();raise
        # Call Stripe after persisting PROCESSING. No automatic retry after uncertain outcome.
        try:
            intent = StripeGateway.retrieve_payment_intent(intent_id)
            raw_metadata = getattr(intent, 'metadata', None)
            metadata = raw_metadata.to_dict() if hasattr(raw_metadata, 'to_dict') else dict(raw_metadata or {})
            if (getattr(intent,'status',None) != 'succeeded' or getattr(intent,'id',None) != intent_id
                or str(metadata.get('order_id','')) != str(ret.order_id)
                or metadata.get('payment_code') != payment.payment_code
                or str(getattr(intent,'currency','')).upper() != refund.currency
                or int(getattr(intent,'amount_received',-1)) != StripeGateway.amount_to_minor_units(payment.amount)):
                raise ValueError('Stripe no coincide con el pago local. Revisión manual.')
            stripe = StripeGateway._stripe()
            result = stripe.Refund.create(payment_intent=intent_id,amount=StripeGateway.amount_to_minor_units(refund.amount),reason='requested_by_customer',metadata={'return_request_id':str(refund.return_request_id),'payment_id':str(refund.payment_id),'tenant_id':str(refund.tenant_id)},idempotency_key=refund.idempotency_key)
            state = getattr(result,'status',None)
            with SessionFromFactory() as other:
                locked = other.scalar(select(ReturnRefund).where(ReturnRefund.id == refund.id).with_for_update())
                locked.stripe_refund_id=result.id
                locked.status='SUCCEEDED' if state == 'succeeded' else ('FAILED' if state in ('failed','canceled') else 'PROCESSING')
                locked.failure_reason=None if locked.status != 'FAILED' else 'Stripe informó fallo.'
                other.commit();other.refresh(locked)
                return locked
        except Exception:
            # Ambiguous network failures MUST remain PROCESSING until verified with Stripe.
            raise

    @staticmethod
    def status(db: Session,user,return_id: int):
        # Consulta de solo lectura: el encargado puede seguir el reembolso de
        # una devolucion de su sucursal, sin autorizar operaciones financieras.
        ret = ReturnService._require_staff_request(db, user, return_id)
        if ret.status != 'RECEIVED':
            raise ValueError('El reembolso solo se consulta tras recibir la devolución.')
        saved = db.scalar(select(ReturnRefund).where(
            ReturnRefund.return_request_id == ret.id,
            ReturnRefund.tenant_id == ret.tenant_id,
        ))
        if saved is None:
            raise LookupError('Reembolso aún no preparado.')
        return saved

    @staticmethod
    def reconcile(db: Session,user,return_id: int):
        ReturnRefundService._check_admin(user)
        if not settings.stripe_secret_key.startswith('sk_test_'):
            raise PermissionError('Solo entorno de pruebas.')
        ret = ReturnRefundService._load(db,user,return_id)
        saved = db.scalar(select(ReturnRefund).where(ReturnRefund.return_request_id == ret.id))
        if saved is None or saved.status not in {'PROCESSING','SUCCEEDED','FAILED','MANUAL_REVIEW'}:
            raise ValueError('Sin reembolso iniciado.')
        payment=db.get(Payment,saved.payment_id)
        stripe=StripeGateway._stripe()
        # Do not issue a second refund, only inspect existing Stripe Refunds.
        matches=[]
        for obj in stripe.Refund.list(payment_intent=payment.external_transaction_id,limit=100).auto_paging_iter():
            raw_metadata = getattr(obj, 'metadata', None)
            md = raw_metadata.to_dict() if hasattr(raw_metadata, 'to_dict') else dict(raw_metadata or {})
            if md.get('return_request_id') == str(ret.id) and md.get('payment_id') == str(payment.id):
                matches.append(obj)
        if len(matches) != 1:
            raise ValueError('Stripe presenta cero o múltiples coincidencias; requiere conciliación manual.')
        obj=matches[0]
        if int(getattr(obj,'amount',-1)) != StripeGateway.amount_to_minor_units(saved.amount) or str(getattr(obj,'currency','')).upper() != saved.currency:
            raise ValueError('Refund Stripe no coincide con importe y moneda.')
        with SessionFromFactory() as other:
            locked=other.scalar(select(ReturnRefund).where(ReturnRefund.id==saved.id).with_for_update())
            locked.stripe_refund_id=obj.id
            state=getattr(obj,'status',None)
            locked.status='SUCCEEDED' if state=='succeeded' else ('FAILED' if state in ('failed','canceled') else 'PROCESSING')
            other.commit();other.refresh(locked);return locked

# Deferred SessionLocal avoids import cycles and never uses caller's in-progress tx across network.
def SessionFromFactory():
    from app.database.session import SessionLocal
    return SessionLocal()
