from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.config import settings
from app.database.session import SessionLocal
from app.models.branch import Branch
from app.models.employee_branch import EmployeeBranch
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product import Product
from app.models.role import Role
from app.models.user import User
from app.services.notification_service import NotificationService
from app.models.product_variant import ProductVariant
from app.models.return_refund import ReturnRefund
from app.models.return_request import ReturnRequest
from app.models.sale import Sale
from app.models.sale_exchange import SaleExchange
from app.models.sale_item import SaleItem
from app.models.sale_return import SaleReturn
from app.models.post_sale_case import (
    PostSaleCase, PostSaleCaseEvent, PostSaleCaseItem,
    PostSaleReplacementItem, PostSaleSettlement,
)
from app.services.return_service import return_policy_for_order
from app.services.stripe_service import StripeGateway

CENT = Decimal("0.01")
RETURN_WINDOW_DAYS = 7
CUSTOMER = "CLIENTE"
STAFF = {"TENANT_ADMIN", "ADMINISTRADOR", "ENCARGADO_SUCURSAL"}
ADMIN = {"TENANT_ADMIN", "ADMINISTRADOR"}
RESERVING_CASE_STATES = {
    "REQUESTED", "APPROVED", "RECEIVED", "INSPECTED",
    "AWAITING_SETTLEMENT", "COMPLETED",
}


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def _now():
    return datetime.now(timezone.utc)


def _role(user) -> str:
    return user.role.name if user.role else ""


class PostSaleService:
    """Unified after-sales workflow for online orders and POS sales."""

    @staticmethod
    def _staff_branch_ids(db: Session, user):
        if _role(user) not in STAFF or user.tenant_id is None:
            raise PermissionError("Tu rol no puede gestionar postventa.")
        if _role(user) in ADMIN:
            return None
        return select(EmployeeBranch.branch_id).join(
            Branch, Branch.id == EmployeeBranch.branch_id
        ).where(
            EmployeeBranch.user_id == user.id,
            EmployeeBranch.is_active.is_(True),
            Branch.is_active.is_(True),
            Branch.tenant_id == user.tenant_id,
        )

    @classmethod
    def _staff_access(cls, db: Session, user, case: PostSaleCase):
        if _role(user) not in STAFF or user.tenant_id is None or case.tenant_id != user.tenant_id:
            raise PermissionError("No tienes permiso para gestionar este caso de postventa.")
        branch_belongs = db.scalar(select(Branch.id).where(
            Branch.id == case.branch_id, Branch.tenant_id == case.tenant_id
        ))
        if branch_belongs is None:
            raise LookupError("La sucursal del caso no pertenece a la empresa.")
        scope = cls._staff_branch_ids(db, user)
        if scope is not None and case.branch_id not in set(db.scalars(scope).all()):
            raise PermissionError("El caso pertenece a otra sucursal.")

    @classmethod
    def _source_access(cls, db: Session, user, branch_id: int, tenant_id: int):
        if user.tenant_id is None or user.tenant_id != tenant_id:
            raise LookupError("La compra no existe en tu empresa.")
        branch_belongs = db.scalar(select(Branch.id).where(
            Branch.id == branch_id, Branch.tenant_id == tenant_id
        ))
        if branch_belongs is None:
            raise LookupError("La sucursal de la compra no pertenece a la empresa.")
        if _role(user) == CUSTOMER:
            return
        # Staff-assisted cases are supported for walk-in sales without a customer account.
        scope = cls._staff_branch_ids(db, user)
        if scope is not None and branch_id not in set(db.scalars(scope).all()):
            raise PermissionError("La compra pertenece a otra sucursal.")

    @staticmethod
    def _load_source(db: Session, channel: str, source_id: int, lock=False):
        if channel == "ONLINE":
            q = select(Order).where(Order.id == source_id)
            if lock:
                q = q.with_for_update()
            source = db.scalar(q)
            if source is None:
                raise LookupError("Pedido online no encontrado.")
            items = db.scalars(select(OrderItem).where(OrderItem.order_id == source.id).order_by(OrderItem.id)).all()
            return source, items, source.branch_id, source.tenant_id, source.customer_id, source.subtotal, source.total_amount
        if channel == "POS":
            q = select(Sale).where(Sale.id == source_id)
            if lock:
                q = q.with_for_update()
            source = db.scalar(q)
            if source is None:
                raise LookupError("Venta presencial no encontrada.")
            items = db.scalars(select(SaleItem).where(SaleItem.sale_id == source.id).order_by(SaleItem.id)).all()
            return source, items, source.branch_id, source.tenant_id, source.customer_id, source.subtotal, source.total_amount
        raise ValueError("Canal de compra inválido.")

    @staticmethod
    def _source_payments(db: Session, channel: str, source_id: int):
        column = Payment.order_id if channel == "ONLINE" else Payment.sale_id
        return db.scalars(select(Payment).where(
            column == source_id, Payment.status == "APPROVED"
        ).order_by(Payment.id)).all()

    @staticmethod
    def _source_policy(channel: str, source):
        now = _now()
        if channel == "ONLINE":
            return return_policy_for_order(source, now)
        created = source.created_at
        if created is not None and created.tzinfo is None:
            created = created.replace(tzinfo=timezone.utc)
        deadline = created + timedelta(days=RETURN_WINDOW_DAYS) if created else None
        if source.status != "PAID":
            reason = "La venta presencial debe estar pagada."
        elif deadline is None:
            reason = "La venta no tiene fecha válida."
        elif created > now:
            reason = "La fecha de la venta está en el futuro."
        elif now >= deadline:
            reason = "El plazo de 7 días desde la venta ha vencido."
        else:
            reason = None
        return {
            "eligible": reason is None,
            "reason": reason,
            "delivered_at": created,
            "return_deadline": deadline,
            "return_window_days": RETURN_WINDOW_DAYS,
        }

    @staticmethod
    def _source_item_variant(channel: str, item):
        return item.product_variant_id

    @staticmethod
    def _line_paid_total(source, item, quantity: int) -> Decimal:
        qty = Decimal(quantity)
        line_qty = Decimal(item.quantity)
        if line_qty <= 0:
            raise ValueError("La cantidad original de la compra es inválida.")
        gross = money(Decimal(str(item.subtotal or 0)) * qty / line_qty)
        subtotal = money(source.subtotal)
        total = money(source.total_amount)
        if subtotal > 0:
            return money(gross * total / subtotal)
        return money(Decimal(str(item.unit_price or 0)) * qty)

    @classmethod
    def _legacy_committed(cls, db: Session, channel: str, source_id: int):
        committed = {}
        if channel == "ONLINE":
            old = db.scalars(select(ReturnRequest).where(
                ReturnRequest.order_id == source_id,
                ReturnRequest.status.in_(("REQUESTED", "APPROVED", "RECEIVED")),
            )).all()
            for req in old:
                for line in req.items:
                    committed[line.order_item_id] = committed.get(line.order_item_id, 0) + line.quantity
        else:
            old = db.scalars(select(SaleReturn).where(
                SaleReturn.sale_id == source_id,
                SaleReturn.status.in_(("REQUESTED", "APPROVED", "RECEIVED", "INSPECTED", "REFUNDED")),
            )).all()
            for req in old:
                for line in req.items:
                    committed[line.sale_item_id] = committed.get(line.sale_item_id, 0) + line.quantity
            # Older direct POS exchanges already consumed the sold units.
            exchanges = db.scalars(select(SaleExchange).where(SaleExchange.sale_id == source_id)).all()
            for exchange in exchanges:
                committed[exchange.sale_item_id] = committed.get(exchange.sale_item_id, 0) + exchange.quantity

        cases = db.scalars(select(PostSaleCase).where(
            (PostSaleCase.order_id == source_id) if channel == "ONLINE" else (PostSaleCase.sale_id == source_id),
            PostSaleCase.status.in_(RESERVING_CASE_STATES),
        ).options(selectinload(PostSaleCase.items))).all()
        for case in cases:
            for line in case.items:
                key = line.order_item_id if channel == "ONLINE" else line.sale_item_id
                if key is not None:
                    committed[key] = committed.get(key, 0) + line.quantity
        return committed

    @classmethod
    def _eligibility_for_source(cls, db, user, channel, source_id, require_customer=True):
        source, items, branch_id, tenant_id, customer_id, subtotal, total = cls._load_source(db, channel, source_id)
        cls._source_access(db, user, branch_id, tenant_id)
        if _role(user) == CUSTOMER:
            if customer_id != user.id:
                raise LookupError("Compra no encontrada para tu cuenta.")
        elif require_customer and _role(user) not in STAFF:
            raise PermissionError("No tienes permiso para consultar esta compra.")
        policy = cls._source_policy(channel, source)
        payments = cls._source_payments(db, channel, source_id)
        reason = policy["reason"]
        if not payments and reason is None:
            reason = "La compra no tiene un pago aprobado registrado."
        eligible = policy["eligible"] and bool(payments)
        committed = cls._legacy_committed(db, channel, source_id)
        lines = []
        any_available = False
        for item in items:
            available = max(0, item.quantity - committed.get(item.id, 0)) if eligible else 0
            any_available = any_available or available > 0
            lines.append({
                "source_item_id": item.id,
                "product_variant_id": item.product_variant_id,
                "purchased_quantity": item.quantity,
                "already_committed_quantity": committed.get(item.id, 0),
                "available_quantity": available,
                "unit_price": money(item.unit_price),
                "subtotal": money(item.subtotal),
            })
        if eligible and not any_available:
            reason = "Todas las unidades ya fueron solicitadas, devueltas o cambiadas."
        return {
            "source_channel": channel,
            "source_id": source.id,
            "source_code": getattr(source, "order_code", None) or getattr(source, "sale_code", None),
            "tenant_id": tenant_id,
            "branch_id": branch_id,
            "customer_id": customer_id,
            "source_status": source.status,
            "eligible": bool(eligible and any_available),
            "reason": reason,
            "delivered_at": policy.get("delivered_at"),
            "return_deadline": policy.get("return_deadline"),
            "return_window_days": policy.get("return_window_days", RETURN_WINDOW_DAYS),
            "currency": "BOB",
            "items": lines,
        }

    @classmethod
    def eligibility(cls, db: Session, user, channel: str, source_id: int):
        if _role(user) != CUSTOMER:
            raise PermissionError("La consulta de elegibilidad desde la app es exclusiva para clientes.")
        return cls._eligibility_for_source(db, user, channel.upper(), source_id)

    @classmethod
    def _event(cls, db, case, actor, action, old_status=None, note=None):
        event = PostSaleCaseEvent(
            case_id=case.id, actor_id=actor.id if actor else None,
            action=action, from_status=old_status, to_status=case.status, note=note,
        )
        case.events.append(event)
        db.add(event)
        return event

    @staticmethod
    def _notify(db: Session, case: PostSaleCase, event: str, *, occurrence: str | None = None):
        """Enqueue notifications inside the state-change transaction (no commit/push here).

        Never notify unrelated tenants or a non-registered walk-in customer.
        """
        label = "devolución" if case.resolution_type == "REFUND" else "cambio"
        code = case.case_code
        money_text = f"Bs {money(case.settlement_amount):,.2f}"
        messages = {
            "REQUESTED": ("Solicitud registrada", f"Recibimos tu solicitud de {label} {code}. Está pendiente de revisión."),
            "APPROVED": ("Solicitud aprobada", f"Tu solicitud de {label} {code} fue aprobada. Consulta los siguientes pasos."),
            "REJECTED": ("Solicitud rechazada", f"Tu solicitud de {label} {code} fue rechazada. Consulta el detalle y el motivo."),
            "RECEIVED": ("Prendas recibidas", f"Recibimos las prendas de tu solicitud {code}."),
            "INSPECTED": ("Prendas inspeccionadas", f"Finalizó la inspección de las prendas de tu solicitud {code}."),
            "EXCHANGE_QUOTED": ("Cambio cotizado", f"Tu cambio {code} tiene una nueva cotización. Consulta las prendas y la diferencia económica antes de continuar."),
            "DIFFERENCE_COLLECTED": ("Diferencia de pago registrada", f"Se registró el pago de {money_text} correspondiente al cambio {code}."),
            "REFUND_PROCESSING": ("Reembolso en procesamiento", f"Estamos procesando el reintegro de {money_text} del caso {code}. Aún no está confirmado."),
            "REFUND_COMPLETED": ("Reembolso registrado", f"Se confirmó el reintegro de {money_text} del caso {code}. El abono en tu cuenta puede tardar según el medio utilizado."),
            "REFUND_FAILED": ("Reembolso requiere atención", f"No se pudo confirmar el reintegro del caso {code}. Nuestro equipo debe revisarlo."),
            "REFUND_MANUAL_REVIEW": ("Reembolso en revisión", f"El reintegro del caso {code} requiere revisión manual. No se ha confirmado el pago."),
            "COMPLETED": ("Postventa finalizada", f"Tu {label} {code} se finalizó correctamente. Puedes revisar el resumen."),
            "CANCELLED": ("Solicitud cancelada", f"Tu solicitud de {label} {code} fue cancelada."),
        }
        content = messages.get(event)
        if content is None:
            return
        if case.customer_id is not None:
            customer = db.get(User, case.customer_id)
            if customer is not None and customer.tenant_id == case.tenant_id:
                title, message = content
                NotificationService.create(
                    db, user_id=customer.id, notification_type="POST_SALE",
                    event=f"POST_SALE_{event}", title=title, message=message,
                    entity_type="POST_SALE_CASE", entity_id=case.id,
                    action_url=f"/post-sale/cases/{case.id}",
                    dedupe_key=f"POST_SALE:{case.id}:{customer.id}:{event}:{occurrence or 'once'}",
                )
        # Operational alerts only for new cases, rejection and problematic refunds.
        if event not in {"REQUESTED", "REFUND_FAILED", "REFUND_MANUAL_REVIEW"}:
            return
        staff_ids = db.scalars(
            select(User.id).join(Role, Role.id == User.role_id).where(
                User.tenant_id == case.tenant_id, User.is_active.is_(True),
                Role.name.in_(ADMIN),
            )
        ).all()
        admin_title = "Nueva solicitud de postventa" if event == "REQUESTED" else "Reembolso que requiere revisión"
        admin_msg = (f"Nueva solicitud de {label} {code} en tu empresa." if event == "REQUESTED"
                     else f"El reintegro del caso {code} requiere atención administrativa.")
        for admin_id in set(staff_ids):
            # Avoid notifying an admin about their own staff-assisted request.
            if event == "REQUESTED" and admin_id == case.requester_id:
                continue
            NotificationService.create(
                db, user_id=admin_id, notification_type="POST_SALE",
                event=f"POST_SALE_{event}", title=admin_title, message=admin_msg,
                entity_type="POST_SALE_CASE", entity_id=case.id,
                action_url=f"/admin/orders/returns?case_id={case.id}",
                dedupe_key=f"POST_SALE:{case.id}:{admin_id}:ADMIN:{event}",
            )

    @classmethod
    def create(cls, db: Session, user, data, staff_assisted=False):
        channel = data.source_channel.upper()
        if len(data.reason.strip()) < 8:
            raise ValueError("Describe el motivo con al menos 8 caracteres.")
        if _role(user) == CUSTOMER and staff_assisted:
            raise PermissionError("Un cliente no puede crear solicitudes asistidas.")
        if _role(user) != CUSTOMER and not staff_assisted:
            raise PermissionError("Solo clientes pueden crear solicitudes desde la app.")
        if staff_assisted and _role(user) not in STAFF:
            raise PermissionError("Solo personal autorizado puede registrar una solicitud asistida.")
        if staff_assisted and channel != "POS":
            raise ValueError("La solicitud asistida está reservada para ventas presenciales.")
        try:
            existing = db.scalar(select(PostSaleCase).where(
                PostSaleCase.idempotency_key == str(data.idempotency_key)
            ).options(selectinload(PostSaleCase.items)))
            if existing is not None:
                if existing.requester_id != user.id:
                    raise PermissionError("La clave de operación ya pertenece a otra solicitud.")
                existing_source_id = existing.order_id if existing.source_channel == "ONLINE" else existing.sale_id
                existing_lines = sorted(
                    ((line.order_item_id if existing.source_channel == "ONLINE" else line.sale_item_id, line.quantity)
                     for line in existing.items)
                )
                requested_lines = sorted((line.source_item_id, line.quantity) for line in data.items)
                if (existing.source_channel != channel or existing_source_id != data.source_id
                    or existing.resolution_type != data.resolution_type
                    or existing.reason != data.reason.strip()
                    or existing_lines != requested_lines):
                    raise ValueError("La clave de operación ya se utilizó con datos diferentes.")
                return cls.detail(db, user, existing.id)
            source, source_items, branch_id, tenant_id, customer_id, subtotal, total = cls._load_source(
                db, channel, data.source_id, lock=True
            )
            cls._source_access(db, user, branch_id, tenant_id)
            if _role(user) == CUSTOMER and customer_id != user.id:
                raise LookupError("Compra no encontrada para tu cuenta.")
            eligibility = cls._eligibility_for_source(db, user, channel, data.source_id)
            if not eligibility["eligible"]:
                raise ValueError(eligibility["reason"] or "La compra no admite esta operación.")
            requested_ids = [line.source_item_id for line in data.items]
            if len(requested_ids) != len(set(requested_ids)):
                raise ValueError("No repitas artículos de la misma compra.")
            by_id = {line["source_item_id"]: line for line in eligibility["items"]}
            source_by_id = {line.id: line for line in source_items}
            original_amount = Decimal("0.00")
            case = PostSaleCase(
                case_code=f"PS-{datetime.now(timezone.utc):%Y%m%d}-{uuid4().hex[:10].upper()}",
                idempotency_key=str(data.idempotency_key),
                tenant_id=tenant_id, customer_id=customer_id, requester_id=user.id,
                branch_id=branch_id, source_channel=channel,
                order_id=source.id if channel == "ONLINE" else None,
                sale_id=source.id if channel == "POS" else None,
                resolution_type=data.resolution_type, status="REQUESTED",
                reason=data.reason.strip(),
            )
            db.add(case)
            db.flush()
            for requested in data.items:
                line = by_id.get(requested.source_item_id)
                source_line = source_by_id.get(requested.source_item_id)
                if line is None or source_line is None or requested.quantity > line["available_quantity"]:
                    raise ValueError("Artículo no elegible o cantidad superior a las unidades disponibles.")
                paid_total = cls._line_paid_total(source, source_line, requested.quantity)
                unit_paid = money(paid_total / Decimal(requested.quantity))
                original_amount += paid_total
                case.items.append(PostSaleCaseItem(
                    order_item_id=source_line.id if channel == "ONLINE" else None,
                    sale_item_id=source_line.id if channel == "POS" else None,
                    quantity=requested.quantity, original_unit_paid=unit_paid,
                    original_total=paid_total,
                ))
            case.original_amount = money(original_amount)
            if case.original_amount <= 0:
                raise ValueError("El importe reconocido de los artículos debe ser mayor que cero.")
            cls._event(db, case, user, "REQUESTED", None, data.reason.strip())
            cls._notify(db, case, "REQUESTED")
            db.commit()
            db.refresh(case)
            return cls._dump(case)
        except Exception:
            db.rollback()
            raise

    @classmethod
    def _get(cls, db, user, case_id, lock=False):
        q = select(PostSaleCase).where(PostSaleCase.id == case_id).options(
            selectinload(PostSaleCase.items),
            selectinload(PostSaleCase.replacement_items).joinedload(PostSaleReplacementItem.variant).joinedload(ProductVariant.product),
            selectinload(PostSaleCase.replacement_items).joinedload(PostSaleReplacementItem.variant).joinedload(ProductVariant.size),
            selectinload(PostSaleCase.replacement_items).joinedload(PostSaleReplacementItem.variant).joinedload(ProductVariant.color),
            selectinload(PostSaleCase.events),
            selectinload(PostSaleCase.settlement),
        )
        if lock:
            q = q.with_for_update()
        case = db.scalar(q)
        if case is None:
            raise LookupError("Caso de postventa no encontrado.")
        if _role(user) == CUSTOMER:
            if case.customer_id != user.id or case.tenant_id != user.tenant_id:
                raise LookupError("Caso de postventa no encontrado.")
        else:
            cls._staff_access(db, user, case)
        return case

    @classmethod
    def _dump(cls, case):
        return {
            "id": case.id,
            "case_code": case.case_code,
            "idempotency_key": case.idempotency_key,
            "tenant_id": case.tenant_id,
            "customer_id": case.customer_id,
            "branch_id": case.branch_id,
            "source_channel": case.source_channel,
            "source_id": case.order_id if case.source_channel == "ONLINE" else case.sale_id,
            "order_id": case.order_id,
            "sale_id": case.sale_id,
            "resolution_type": case.resolution_type,
            "status": case.status,
            "reason": case.reason,
            "staff_note": case.staff_note,
            "original_amount": money(case.original_amount),
            "replacement_amount": money(case.replacement_amount),
            "difference_amount": money(case.difference_amount),
            "settlement_kind": case.settlement_kind,
            "settlement_amount": money(case.settlement_amount),
            "settlement_status": case.settlement_status,
            "created_at": case.created_at,
            "reviewed_at": case.reviewed_at,
            "received_at": case.received_at,
            "inspected_at": case.inspected_at,
            "completed_at": case.completed_at,
            "items": [{
                "id": line.id,
                "source_item_id": line.order_item_id if case.source_channel == "ONLINE" else line.sale_item_id,
                "quantity": line.quantity,
                "original_unit_paid": money(line.original_unit_paid),
                "original_total": money(line.original_total),
                "condition": line.condition,
                "inspection_note": line.inspection_note,
                "inventory_movement_id": line.inventory_movement_id,
            } for line in case.items],
            "replacement_items": [{
                "id": line.id, "product_variant_id": line.product_variant_id,
                "quantity": line.quantity, "unit_price": money(line.unit_price),
                "subtotal": money(line.subtotal),
                "inventory_movement_id": line.inventory_movement_id,
                # Información comercial del reemplazo, sin sustituir el ID interno
                # que utilizan inventario y liquidación.
                "product_name": line.variant.product.name if line.variant and line.variant.product else None,
                "product_code": line.variant.product.code if line.variant and line.variant.product else None,
                "sku": line.variant.sku if line.variant else None,
                "size": line.variant.size.name if line.variant and line.variant.size else None,
                "color": line.variant.color.name if line.variant and line.variant.color else None,
                "image_url": (line.variant.image_url or line.variant.product.cover_image_url)
                    if line.variant and line.variant.product else None,
            } for line in case.replacement_items],
            "settlement": None if case.settlement is None else {
                "id": case.settlement.id, "kind": case.settlement.kind,
                "amount": money(case.settlement.amount), "currency": case.settlement.currency,
                "method": case.settlement.method, "mode": case.settlement.mode,
                "status": case.settlement.status, "reference": case.settlement.reference,
                "stripe_refund_id": case.settlement.stripe_refund_id,
                "completed_at": case.settlement.completed_at,
            },
            "events": [{
                "id": e.id, "actor_id": e.actor_id, "action": e.action,
                "from_status": e.from_status, "to_status": e.to_status,
                "note": e.note, "created_at": e.created_at,
            } for e in case.events],
        }

    @classmethod
    def detail(cls, db, user, case_id):
        return cls._dump(cls._get(db, user, case_id))

    @classmethod
    def list(cls, db, user, mine=False, status=None, channel=None):
        q = select(PostSaleCase).options(
            selectinload(PostSaleCase.items),
            selectinload(PostSaleCase.replacement_items).joinedload(PostSaleReplacementItem.variant).joinedload(ProductVariant.product),
            selectinload(PostSaleCase.replacement_items).joinedload(PostSaleReplacementItem.variant).joinedload(ProductVariant.size),
            selectinload(PostSaleCase.replacement_items).joinedload(PostSaleReplacementItem.variant).joinedload(ProductVariant.color),
            selectinload(PostSaleCase.settlement),
        ).where(PostSaleCase.tenant_id == user.tenant_id)
        if _role(user) == CUSTOMER or mine:
            q = q.where(PostSaleCase.customer_id == user.id)
        elif _role(user) in STAFF:
            scope = cls._staff_branch_ids(db, user)
            if scope is not None:
                q = q.where(PostSaleCase.branch_id.in_(scope))
        else:
            raise PermissionError("No tienes acceso a postventa.")
        if status:
            q = q.where(PostSaleCase.status == status.upper())
        if channel:
            q = q.where(PostSaleCase.source_channel == channel.upper())
        rows = db.scalars(q.order_by(PostSaleCase.id.desc()).limit(200)).all()
        return [cls._dump(row) for row in rows]

    @classmethod
    def decide(cls, db, user, case_id, data):
        try:
            case = cls._get(db, user, case_id, lock=True)
            if _role(user) not in STAFF:
                raise PermissionError("Solo el personal de sucursal puede revisar solicitudes.")
            if case.status != "REQUESTED":
                raise ValueError("La solicitud ya fue revisada.")
            old = case.status
            case.status = "APPROVED" if data.approve else "REJECTED"
            case.staff_note = data.note.strip() if data.note else case.staff_note
            case.reviewed_by = user.id
            case.reviewed_at = _now()
            cls._event(db, case, user, "APPROVED" if data.approve else "REJECTED", old, data.note)
            cls._notify(db, case, "APPROVED" if data.approve else "REJECTED")
            db.commit()
            db.refresh(case)
            return cls._dump(case)
        except Exception:
            db.rollback()
            raise

    @classmethod
    def receive(cls, db, user, case_id, note=None):
        try:
            case = cls._get(db, user, case_id, lock=True)
            if _role(user) not in STAFF:
                raise PermissionError("Solo el personal de sucursal puede recibir artículos.")
            if case.status != "APPROVED":
                raise ValueError("Solo se reciben solicitudes aprobadas.")
            old = case.status
            case.status = "RECEIVED"
            case.received_by = user.id
            case.received_at = _now()
            if note:
                case.staff_note = note.strip()
            cls._event(db, case, user, "RECEIVED", old, note)
            cls._notify(db, case, "RECEIVED")
            db.commit()
            db.refresh(case)
            return cls._dump(case)
        except Exception:
            db.rollback()
            raise

    @classmethod
    def inspect(cls, db, user, case_id, data):
        try:
            case = cls._get(db, user, case_id, lock=True)
            if _role(user) not in STAFF:
                raise PermissionError("Solo el personal de sucursal puede inspeccionar artículos.")
            if case.status != "RECEIVED":
                raise ValueError("Primero registra la recepción física de los artículos.")
            supplied = {line.case_item_id: line for line in data.items}
            if len(supplied) != len(data.items) or set(supplied) != {line.id for line in case.items}:
                raise ValueError("Debes inspeccionar cada artículo solicitado exactamente una vez.")
            for line in case.items:
                decision = supplied[line.id]
                line.condition = decision.condition
                line.inspection_note = decision.note
            old = case.status
            case.status = "INSPECTED"
            case.inspected_by = user.id
            case.inspected_at = _now()
            if case.resolution_type == "REFUND":
                case.settlement_kind = "REFUND"
                case.settlement_amount = money(case.original_amount)
                case.settlement_status = "PENDING"
                case.status = "AWAITING_SETTLEMENT"
            cls._event(db, case, user, "INSPECTED", old, "Inspección de todos los artículos registrada.")
            cls._notify(db, case, "INSPECTED")
            db.commit()
            db.refresh(case)
            return cls._dump(case)
        except Exception:
            db.rollback()
            raise

    @classmethod
    def quote_exchange(cls, db, user, case_id, data):
        try:
            case = cls._get(db, user, case_id, lock=True)
            if _role(user) not in STAFF:
                raise PermissionError("Solo el personal autorizado puede cotizar un cambio.")
            if case.resolution_type != "EXCHANGE" or case.status not in {"INSPECTED", "AWAITING_SETTLEMENT"}:
                raise ValueError("La cotización solo está disponible para cambios inspeccionados.")
            if case.settlement is not None:
                raise ValueError("Ya existe una liquidación registrada; no se puede cambiar la cotización.")
            if not data.items:
                raise ValueError("Selecciona al menos una prenda de reemplazo.")
            variant_ids = [x.product_variant_id for x in data.items]
            if len(variant_ids) != len(set(variant_ids)):
                raise ValueError("No repitas variantes de reemplazo.")
            source, _, branch_id, tenant_id, _, _, _ = cls._load_source(
                db, case.source_channel, case.order_id if case.source_channel == "ONLINE" else case.sale_id
            )
            original_variants = set()
            for item in case.items:
                src_line = db.get(OrderItem, item.order_item_id) if case.source_channel == "ONLINE" else db.get(SaleItem, item.sale_item_id)
                if src_line is None:
                    raise ValueError("Artículo original inconsistente.")
                original_variants.add(src_line.product_variant_id)
            if original_variants.intersection(variant_ids):
                raise ValueError("Elige una variante distinta de las prendas que estás devolviendo.")
            for old in list(case.replacement_items):
                db.delete(old)
            replacement_total = Decimal("0.00")
            for line in data.items:
                variant = db.scalar(select(ProductVariant).where(ProductVariant.id == line.product_variant_id))
                product = db.get(Product, variant.product_id) if variant else None
                if variant is None or product is None or not variant.is_active or not product.is_active:
                    raise LookupError("Una variante de reemplazo no existe o está inactiva.")
                if product.tenant_id != tenant_id:
                    raise PermissionError("La prenda de reemplazo pertenece a otra empresa.")
                inventory = db.scalar(select(Inventory).where(
                    Inventory.branch_id == branch_id,
                    Inventory.product_variant_id == variant.id,
                    Inventory.is_active.is_(True),
                ))
                if inventory is None or inventory.available_quantity < line.quantity:
                    raise ValueError("No hay stock suficiente de una de las prendas de reemplazo.")
                unit = money(Decimal(str(product.base_price)) + Decimal(str(variant.additional_price or 0)))
                subtotal = money(unit * line.quantity)
                replacement_total += subtotal
                case.replacement_items.append(PostSaleReplacementItem(
                    product_variant_id=variant.id, quantity=line.quantity,
                    unit_price=unit, subtotal=subtotal,
                ))
            case.replacement_amount = money(replacement_total)
            case.difference_amount = money(replacement_total - case.original_amount)
            if case.difference_amount > 0:
                case.settlement_kind = "COLLECT"
                case.settlement_amount = case.difference_amount
                case.settlement_status = "PENDING"
            elif case.difference_amount < 0:
                case.settlement_kind = "REFUND"
                case.settlement_amount = abs(case.difference_amount)
                case.settlement_status = "PENDING"
            else:
                case.settlement_kind = "NONE"
                case.settlement_amount = Decimal("0.00")
                case.settlement_status = "NOT_REQUIRED"
            old = case.status
            case.status = "AWAITING_SETTLEMENT"
            quote_event = cls._event(
                db, case, user, "EXCHANGE_QUOTED", old,
                f"Valor original {case.original_amount}; reemplazo {case.replacement_amount}; diferencia {case.difference_amount}.",
            )
            db.flush()
            cls._notify(db, case, "EXCHANGE_QUOTED", occurrence=str(quote_event.id))
            db.commit()
            db.refresh(case)
            return cls._dump(case)
        except Exception:
            db.rollback()
            raise

    @classmethod
    def _prior_refunded_amount(cls, db, case):
        amount = Decimal("0.00")
        if case.source_channel == "ONLINE":
            old = db.scalar(
                select(func.coalesce(func.sum(ReturnRefund.amount), 0))
                .join(ReturnRequest, ReturnRequest.id == ReturnRefund.return_request_id)
                .where(
                    ReturnRequest.order_id == case.order_id,
                    ReturnRefund.status.in_(("PREPARED", "PROCESSING", "SUCCEEDED", "MANUAL_REVIEW")),
                )
            )
        else:
            old = db.scalar(select(func.coalesce(func.sum(SaleReturn.requested_amount), 0)).where(
                SaleReturn.sale_id == case.sale_id, SaleReturn.status == "REFUNDED"
            ))
        amount += money(old or 0)
        other = db.scalar(select(func.coalesce(func.sum(PostSaleSettlement.amount), 0))
            .join(PostSaleCase, PostSaleCase.id == PostSaleSettlement.case_id)
            .where(
                PostSaleCase.id != case.id,
                PostSaleCase.source_channel == case.source_channel,
                (PostSaleCase.order_id == case.order_id) if case.source_channel == "ONLINE" else (PostSaleCase.sale_id == case.sale_id),
                PostSaleSettlement.kind == "REFUND",
                PostSaleSettlement.status.in_(("PROCESSING", "COMPLETED", "MANUAL_REVIEW")),
            ))
        amount += money(other or 0)
        return amount

    @classmethod
    def _validate_refund_capacity(cls, db, case, amount):
        source, _, _, _, _, _, total = cls._load_source(
            db, case.source_channel, case.order_id if case.source_channel == "ONLINE" else case.sale_id
        )
        approved = cls._source_payments(db, case.source_channel, source.id)
        paid_total = sum((money(p.amount) for p in approved), Decimal("0.00"))
        source_total = money(total)
        if not approved or paid_total < source_total:
            raise ValueError("Los pagos aprobados no cubren el total de la compra. Requiere conciliación manual.")
        refund_cap = min(paid_total, source_total)
        if cls._prior_refunded_amount(db, case) + amount > refund_cap:
            raise ValueError("El reintegro acumulado superaría el importe neto de la compra.")
        return approved, refund_cap

    @classmethod
    def settle(cls, db, user, case_id, data):
        stripe_work = None
        try:
            case = cls._get(db, user, case_id, lock=True)
            if case.status != "AWAITING_SETTLEMENT":
                raise ValueError("El caso todavía no está listo para liquidación.")
            if case.settlement is not None:
                raise ValueError("Ya existe una liquidación para este caso.")
            kind = case.settlement_kind
            amount = money(case.settlement_amount)
            if kind == "NONE" or amount <= 0:
                raise ValueError("Este caso no requiere un movimiento de dinero.")
            if money(data.amount) != amount:
                raise ValueError("El importe enviado no coincide con la diferencia calculada por el servidor.")
            source_id = case.order_id if case.source_channel == "ONLINE" else case.sale_id
            payments = cls._source_payments(db, case.source_channel, source_id)

            if kind == "COLLECT":
                if _role(user) not in STAFF:
                    raise PermissionError("Solo el personal autorizado puede registrar el cobro de una diferencia.")
                if not data.method:
                    raise ValueError("Indica el método de pago de la diferencia.")
                if data.method != "CASH" and (not data.reference or len(data.reference.strip()) < 4):
                    raise ValueError("Registra una referencia de pago válida para tarjeta, QR o transferencia.")
                settlement = PostSaleSettlement(
                    case_id=case.id, tenant_id=case.tenant_id, kind="COLLECT",
                    amount=amount, currency="BOB", method=data.method,
                    mode="BRANCH_COLLECTION", status="COMPLETED",
                    reference=data.reference.strip() if data.reference else None,
                    idempotency_key=f"post-sale-{case.id}-collect-v1",
                    created_by=user.id, completed_by=user.id, completed_at=_now(),
                )
                case.settlement_status = "COMPLETED"
                case.settlement = settlement
                db.add(settlement)
                cls._event(db, case, user, "DIFFERENCE_COLLECTED", case.status, data.reference)
                cls._notify(db, case, "DIFFERENCE_COLLECTED")
                db.commit()
                db.refresh(case)
                return cls._dump(case)

            if kind != "REFUND":
                raise ValueError("Tipo de liquidación no soportado.")
            if _role(user) not in ADMIN:
                raise PermissionError("Solo el administrador de la empresa puede autorizar reintegros.")
            cls._validate_refund_capacity(db, case, amount)

            mode = data.mode
            if mode == "DEMO_LOCAL":
                if os.getenv("FASHIONSTORE_ENABLE_DEMO_REFUNDS", "").lower() != "true":
                    raise PermissionError("Los reintegros demo están deshabilitados en este entorno.")
                if not payments or any((p.provider or "").upper() != "DEMO_LOCAL" for p in payments):
                    raise ValueError("Solo se pueden simular reintegros de pagos identificados como DEMO_LOCAL.")
                if data.reference:
                    reference = data.reference.strip()
                else:
                    reference = f"DEMO-POSTSALE-{case.id}"
                settlement = PostSaleSettlement(
                    case_id=case.id, tenant_id=case.tenant_id, kind="REFUND",
                    amount=amount, currency="BOB", mode=mode, status="COMPLETED",
                    reference=reference, idempotency_key=f"post-sale-{case.id}-refund-v1",
                    created_by=user.id, completed_by=user.id, completed_at=_now(),
                )
                case.settlement_status = "COMPLETED"
                case.settlement = settlement
                db.add(settlement)
                cls._event(db, case, user, "DEMO_REFUND_CONFIRMED", case.status, reference)
                cls._notify(db, case, "REFUND_COMPLETED")
                db.commit()
                db.refresh(case)
                return cls._dump(case)

            if mode == "EXTERNAL_MANUAL":
                if not data.reference or len(data.reference.strip()) < 6:
                    raise ValueError("Se requiere una constancia externa de al menos 6 caracteres.")
                reference = data.reference.strip()
                settlement = PostSaleSettlement(
                    case_id=case.id, tenant_id=case.tenant_id, kind="REFUND",
                    amount=amount, currency="BOB", mode=mode, status="COMPLETED",
                    reference=reference, idempotency_key=f"post-sale-{case.id}-refund-v1",
                    created_by=user.id, completed_by=user.id, completed_at=_now(),
                )
                case.settlement_status = "COMPLETED"
                case.settlement = settlement
                db.add(settlement)
                cls._event(db, case, user, "EXTERNAL_REFUND_RECORDED", case.status, reference)
                cls._notify(db, case, "REFUND_COMPLETED")
                db.commit()
                db.refresh(case)
                return cls._dump(case)

            if mode == "STRIPE_TEST":
                if case.source_channel != "ONLINE" or not settings.stripe_secret_key.startswith("sk_test_"):
                    raise PermissionError("Stripe automático está disponible únicamente con pagos online y clave sk_test_.")
                stripe_payments = [p for p in payments if (p.provider or "").upper() == "STRIPE"]
                if len(stripe_payments) != 1:
                    raise ValueError("Se requiere exactamente un pago Stripe aprobado para reembolsar automáticamente.")
                payment = stripe_payments[0]
                intent_id = payment.external_transaction_id or ""
                if not intent_id.startswith("pi_"):
                    raise ValueError("El pago no tiene un PaymentIntent válido.")
                intent = StripeGateway.retrieve_payment_intent(intent_id)
                raw_metadata = getattr(intent, "metadata", None)
                metadata = raw_metadata.to_dict() if hasattr(raw_metadata, "to_dict") else dict(raw_metadata or {})
                if (
                    getattr(intent, "status", None) != "succeeded"
                    or getattr(intent, "id", None) != intent_id
                    or str(metadata.get("order_id", "")) != str(case.order_id)
                    or metadata.get("payment_code") != payment.payment_code
                    or str(getattr(intent, "currency", "")).upper() != "BOB"
                    or int(getattr(intent, "amount_received", -1)) != StripeGateway.amount_to_minor_units(payment.amount)
                    or amount > money(payment.amount)
                ):
                    raise ValueError("Stripe no coincide con el pago original. Revisión manual requerida.")
                settlement = PostSaleSettlement(
                    case_id=case.id, tenant_id=case.tenant_id, kind="REFUND",
                    amount=amount, currency="BOB", mode=mode, status="PROCESSING",
                    idempotency_key=f"fashionstore-post-sale-{case.id}-refund-v1",
                    created_by=user.id,
                )
                case.settlement_status = "PROCESSING"
                case.settlement = settlement
                db.add(settlement)
                cls._event(db, case, user, "STRIPE_REFUND_PROCESSING", case.status, "Reembolso Stripe de prueba iniciado.")
                cls._notify(db, case, "REFUND_PROCESSING")
                db.commit()
                db.refresh(settlement)
                stripe_work = (settlement.id, intent_id, amount, case.id, payment.id, case.tenant_id)
            else:
                raise ValueError("Selecciona DEMO_LOCAL, EXTERNAL_MANUAL o STRIPE_TEST.")
        except Exception:
            db.rollback()
            raise

        if stripe_work:
            settlement_id, intent_id, amount, case_id, payment_id, tenant_id = stripe_work
            try:
                stripe = StripeGateway._stripe()
                result = stripe.Refund.create(
                    payment_intent=intent_id,
                    amount=StripeGateway.amount_to_minor_units(amount),
                    reason="requested_by_customer",
                    metadata={
                        "post_sale_case_id": str(case_id),
                        "payment_id": str(payment_id),
                        "tenant_id": str(tenant_id),
                    },
                    idempotency_key=f"fashionstore-post-sale-{case_id}-refund-v1",
                )
                state = getattr(result, "status", None)
                with SessionLocal() as other:
                    saved = other.scalar(select(PostSaleSettlement).where(PostSaleSettlement.id == settlement_id).with_for_update())
                    saved.stripe_refund_id = result.id
                    saved.status = "COMPLETED" if state == "succeeded" else ("FAILED" if state in ("failed", "canceled") else "PROCESSING")
                    saved.completed_at = _now() if saved.status == "COMPLETED" else None
                    saved.failure_reason = "Stripe informó fallo." if saved.status == "FAILED" else None
                    parent = other.get(PostSaleCase, case_id)
                    parent.settlement_status = saved.status
                    if saved.status == "COMPLETED":
                        saved.completed_by = user.id
                    if saved.status in {"COMPLETED", "FAILED"}:
                        cls._notify(other, parent, "REFUND_COMPLETED" if saved.status == "COMPLETED" else "REFUND_FAILED")
                    other.commit()
                    other.refresh(parent)
                    return PostSaleService._dump(parent)
            except Exception:
                # Keep PROCESSING. Reconcile with Stripe; never issue a blind retry.
                raise

    @classmethod
    def reconcile_stripe(cls, db, user, case_id):
        if _role(user) not in ADMIN:
            raise PermissionError("Solo el administrador puede conciliar reembolsos Stripe.")
        case = cls._get(db, user, case_id, lock=True)
        settlement = case.settlement
        if settlement is None or settlement.mode != "STRIPE_TEST" or settlement.status not in {"PROCESSING", "COMPLETED", "FAILED", "MANUAL_REVIEW"}:
            raise ValueError("No existe un reembolso Stripe que requiera conciliación.")
        payments = cls._source_payments(db, "ONLINE", case.order_id)
        stripe_payments = [p for p in payments if (p.provider or "").upper() == "STRIPE"]
        if len(stripe_payments) != 1:
            raise ValueError("No se pudo identificar un único pago Stripe.")
        stripe = StripeGateway._stripe()
        matches = []
        for refund in stripe.Refund.list(payment_intent=stripe_payments[0].external_transaction_id, limit=100).auto_paging_iter():
            raw = getattr(refund, "metadata", None)
            md = raw.to_dict() if hasattr(raw, "to_dict") else dict(raw or {})
            if md.get("post_sale_case_id") == str(case.id) and md.get("payment_id") == str(stripe_payments[0].id):
                matches.append(refund)
        previous_status = settlement.status
        if len(matches) != 1:
            settlement.status = "MANUAL_REVIEW"
            settlement.failure_reason = "Stripe presenta cero o múltiples coincidencias."
            case.settlement_status = "MANUAL_REVIEW"
            if previous_status != "MANUAL_REVIEW":
                cls._notify(db, case, "REFUND_MANUAL_REVIEW")
            db.commit()
            raise ValueError("Stripe presenta cero o múltiples coincidencias; requiere revisión manual.")
        found = matches[0]
        if int(getattr(found, "amount", -1)) != StripeGateway.amount_to_minor_units(settlement.amount) or str(getattr(found, "currency", "")).upper() != "BOB":
            settlement.status = "MANUAL_REVIEW"
            settlement.failure_reason = "El importe de Stripe no coincide."
            case.settlement_status = "MANUAL_REVIEW"
        else:
            state = getattr(found, "status", None)
            settlement.stripe_refund_id = found.id
            settlement.status = "COMPLETED" if state == "succeeded" else ("FAILED" if state in ("failed", "canceled") else "PROCESSING")
            settlement.completed_at = _now() if settlement.status == "COMPLETED" else None
            case.settlement_status = settlement.status
        if previous_status != settlement.status and settlement.status in {"COMPLETED", "FAILED", "MANUAL_REVIEW"}:
            cls._notify(db, case, {"COMPLETED": "REFUND_COMPLETED", "FAILED": "REFUND_FAILED", "MANUAL_REVIEW": "REFUND_MANUAL_REVIEW"}[settlement.status])
        db.commit()
        db.refresh(case)
        return cls._dump(case)

    @classmethod
    def complete(cls, db, user, case_id):
        try:
            case = cls._get(db, user, case_id, lock=True)
            if _role(user) not in STAFF:
                raise PermissionError("Solo el personal autorizado puede cerrar el caso.")
            if case.status != "AWAITING_SETTLEMENT":
                raise ValueError("El caso todavía no está listo para completarse.")
            if case.settlement_kind == "NONE":
                if case.settlement_status != "NOT_REQUIRED":
                    raise ValueError("El estado financiero del cambio es inconsistente.")
            elif case.settlement_status != "COMPLETED":
                raise ValueError("Primero debe completarse el cobro o reintegro correspondiente.")
            if any(line.condition is None for line in case.items):
                raise ValueError("Falta inspeccionar uno o más artículos.")
            if case.resolution_type == "EXCHANGE" and not case.replacement_items:
                raise ValueError("El cambio todavía no tiene prendas de reemplazo cotizadas.")

            source_id = case.order_id if case.source_channel == "ONLINE" else case.sale_id
            source, source_items, branch_id, tenant_id, _, _, _ = cls._load_source(db, case.source_channel, source_id, lock=True)
            source_by_id = {line.id: line for line in source_items}

            # Lock every affected inventory row in stable variant order.
            returned = []
            for line in case.items:
                src = source_by_id.get(line.order_item_id if case.source_channel == "ONLINE" else line.sale_item_id)
                if src is None:
                    raise ValueError("Artículo original inconsistente.")
                if line.condition == "RESELLABLE":
                    returned.append((src.product_variant_id, line.quantity, line))

            replacement = [(line.product_variant_id, line.quantity, line) for line in case.replacement_items]
            variant_ids = sorted({x[0] for x in returned + replacement})
            inventories = db.scalars(select(Inventory).where(
                Inventory.branch_id == branch_id,
                Inventory.product_variant_id.in_(variant_ids),
                Inventory.is_active.is_(True),
            ).order_by(Inventory.product_variant_id).with_for_update()).all() if variant_ids else []
            by_variant = {inv.product_variant_id: inv for inv in inventories}
            if set(variant_ids) != set(by_variant):
                raise ValueError("Falta inventario activo para alguna variante; se requiere revisión manual.")

            old_status = case.status
            for variant_id, quantity, line in returned:
                inv = by_variant[variant_id]
                before, reserved = inv.stock_quantity, inv.reserved_quantity
                after = before + quantity
                if inv.maximum_stock is not None and after > inv.maximum_stock:
                    raise ValueError("La reincorporación superaría el stock máximo configurado.")
                inv.stock_quantity = after
                movement = InventoryMovement(
                    inventory_id=inv.id, movement_type="RETURN_IN", quantity=quantity,
                    stock_before=before, stock_after=after, reserved_before=reserved, reserved_after=reserved,
                    user_id=user.id, reference_type="POST_SALE_CASE", reference_id=case.id,
                    reference_code=case.case_code, reason="Devolución postventa inspeccionada y apta",
                    notes=f"Artículo del caso {case.case_code}",
                )
                db.add(movement)
                db.flush()
                line.inventory_movement_id = movement.id

            for variant_id, quantity, line in replacement:
                inv = by_variant[variant_id]
                if inv.stock_quantity - inv.reserved_quantity < quantity:
                    raise ValueError("El stock de una prenda de reemplazo cambió; vuelve a cotizar.")
                before, reserved = inv.stock_quantity, inv.reserved_quantity
                after = before - quantity
                inv.stock_quantity = after
                movement = InventoryMovement(
                    inventory_id=inv.id, movement_type="SALE", quantity=quantity,
                    stock_before=before, stock_after=after, reserved_before=reserved, reserved_after=reserved,
                    user_id=user.id, reference_type="POST_SALE_CASE", reference_id=case.id,
                    reference_code=case.case_code, reason="Entrega de prenda por cambio postventa",
                    notes=f"Reemplazo del caso {case.case_code}",
                )
                db.add(movement)
                db.flush()
                line.inventory_movement_id = movement.id

            # A source purchase is marked REFUNDED only when accumulated full-refund
            # settlements reach the net amount originally paid. Exchanges never do this.
            if case.resolution_type == "REFUND" and case.settlement_kind == "REFUND" and case.settlement is not None:
                source_total = money(source.total_amount)
                refunded_before = cls._prior_refunded_amount(db, case)
                if refunded_before + money(case.settlement.amount) >= source_total:
                    source.status = "REFUNDED"

            case.status = "COMPLETED"
            case.completed_by = user.id
            case.completed_at = _now()
            cls._event(db, case, user, "COMPLETED", old_status, "Postventa finalizada; inventario actualizado de forma auditada.")
            cls._notify(db, case, "COMPLETED")
            db.commit()
            db.refresh(case)
            return cls._dump(case)
        except Exception:
            db.rollback()
            raise

    @classmethod
    def cancel(cls, db, user, case_id, reason=None):
        try:
            case = cls._get(db, user, case_id, lock=True)
            if _role(user) != CUSTOMER or case.customer_id != user.id:
                raise PermissionError("Solo el cliente propietario puede cancelar desde la app.")
            if case.status != "REQUESTED":
                raise ValueError("Solo se pueden cancelar solicitudes todavía no revisadas.")
            old = case.status
            case.status = "CANCELLED"
            cls._event(db, case, user, "CANCELLED", old, reason)
            cls._notify(db, case, "CANCELLED")
            db.commit()
            db.refresh(case)
            return cls._dump(case)
        except Exception:
            db.rollback()
            raise
