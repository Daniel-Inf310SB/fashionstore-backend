from datetime import datetime, timedelta, timezone
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.employee_branch import EmployeeBranch
from app.models.branch import Branch
from app.models.return_request import ReturnRequest, ReturnItem
from app.models.post_sale_case import PostSaleCase
from app.models.user import User

# A received return still consumes its units, even after a successful refund.
# Only cancelled or rejected requests release units for a new request.
ACTIVE = {"REQUESTED", "APPROVED", "RECEIVED"}
RESERVING_STATES = ACTIVE


def remaining_return_quantities(purchased, requested):
    """Compute available quantities without losing already received requests."""
    remaining = {}
    for item_id, quantity in purchased.items():
        if quantity < 0 or requested.get(item_id, 0) < 0:
            raise ValueError("Cantidades inconsistentes.")
        remaining[item_id] = max(0, quantity - requested.get(item_id, 0))
    return remaining

# Las devoluciones ordinarias aplican a productos entregados, no a pedidos por preparar.
RETURN_WINDOW_DAYS = 7
ELIGIBLE = {"DELIVERED", "COMPLETED"}


def return_policy_for_order(order: Order, now: datetime | None = None) -> dict:
    """Política comercial de 7 días exactos desde la entrega efectiva.

    Para PICKUP, el evento de entrega es COMPLETED y se registra en completed_at.
    Para DELIVERY, el evento de entrega es DELIVERED y se registra en delivered_at.
    No sustituir fechas faltantes por created_at o paid_at: no son entregas.
    """
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    delivery_type = str(getattr(order, "delivery_type", "") or "").upper()
    status = str(getattr(order, "status", "") or "").upper()
    delivered_at = (getattr(order, "completed_at", None) if delivery_type == "PICKUP"
                    else getattr(order, "delivered_at", None))
    if delivered_at is not None and delivered_at.tzinfo is None:
        delivered_at = delivered_at.replace(tzinfo=timezone.utc)
    deadline = delivered_at + timedelta(days=RETURN_WINDOW_DAYS) if delivered_at else None
    if status not in ELIGIBLE or (delivery_type == "PICKUP" and status != "COMPLETED"):
        reason = "La compra todavía no registra la entrega final o no admite devoluciones en este estado."
    elif delivered_at is None:
        reason = "No existe una fecha de entrega confirmada. Solicita su verificación a la tienda."
    elif now < delivered_at:
        reason = "La fecha registrada de entrega está en el futuro. Solicita su verificación a la tienda."
    elif now >= deadline:
        reason = "El plazo de 7 días desde la entrega ha vencido."
    else:
        reason = None
    return {"delivered_at": delivered_at, "return_deadline": deadline,
            "return_window_days": RETURN_WINDOW_DAYS, "reason": reason, "eligible": reason is None}


class ReturnService:
    @staticmethod
    def _tenant(user):
        if user.tenant_id is None:
            raise PermissionError("Debes operar dentro de una empresa.")
        return user.tenant_id

    @staticmethod
    def _admin(user):
        if user.role is None or user.role.name not in {"TENANT_ADMIN", "ADMINISTRADOR"}:
            raise PermissionError("Solo el administrador de la empresa puede revisar devoluciones.")

    @staticmethod
    def _staff(user):
        """Personal que puede tramitar devoluciones, no ejecutar reembolsos."""
        if not user.role or user.role.name not in {"TENANT_ADMIN", "ADMINISTRADOR", "ENCARGADO_SUCURSAL"}:
            raise PermissionError("Tu rol no puede gestionar devoluciones.")

    @staticmethod
    def _staff_scope(db: Session, user: User):
        """Subconsulta de sucursales ACTIVAS asignadas al encargado en su empresa."""
        ReturnService._staff(user)
        if user.role.name != "ENCARGADO_SUCURSAL":
            return None  # Administrador: todas las sucursales de su tenant.
        return (
            select(EmployeeBranch.branch_id)
            .join(Branch, Branch.id == EmployeeBranch.branch_id)
            .where(
                EmployeeBranch.user_id == user.id,
                EmployeeBranch.is_active.is_(True),
                Branch.tenant_id == ReturnService._tenant(user),
                Branch.is_active.is_(True),
            )
        )

    @staticmethod
    def _staff_request_query(db: Session, user: User):
        scope = ReturnService._staff_scope(db, user)
        query = (
            select(ReturnRequest)
            .join(Order, Order.id == ReturnRequest.order_id)
            .where(
                ReturnRequest.tenant_id == ReturnService._tenant(user),
                Order.tenant_id == ReturnRequest.tenant_id,
            )
        )
        if scope is not None:
            query = query.where(Order.branch_id.in_(scope))
        return query

    @staticmethod
    def _require_staff_request(db: Session, user: User, request_id: int, lock=False):
        query = ReturnService._staff_request_query(db, user).where(ReturnRequest.id == request_id)
        if lock:
            query = query.with_for_update(of=ReturnRequest)
        request = db.scalar(query)
        if request is None:
            raise LookupError("Devolución no encontrada entre las sucursales autorizadas.")
        return request

    @staticmethod
    def _get(db: Session, request_id: int, user: User, lock=False):
        q = select(ReturnRequest).where(ReturnRequest.id == request_id, ReturnRequest.tenant_id == ReturnService._tenant(user))
        if lock:
            q = q.with_for_update()
        result = db.scalar(q)
        if result is None:
            raise LookupError("Solicitud no encontrada en tu empresa.")
        return result

    @staticmethod
    def _customer_order(db: Session, user: User, order_id: int, lock=False):
        if not user.role or user.role.name != "CLIENTE":
            raise PermissionError("Solo clientes pueden consultar sus devoluciones.")
        query = select(Order).where(
            Order.id == order_id,
            Order.tenant_id == ReturnService._tenant(user),
            Order.customer_id == user.id,
        )
        if lock:
            query = query.with_for_update()
        order = db.scalar(query)
        if order is None:
            raise LookupError("Compra no encontrada para el cliente.")
        return order

    @staticmethod
    def _returnable_quantities(db: Session, order: Order):
        items = db.scalars(select(OrderItem).where(OrderItem.order_id == order.id)).all()
        by_id = {item.id: item for item in items}
        requests = db.scalars(select(ReturnRequest).where(
            ReturnRequest.order_id == order.id,
            ReturnRequest.tenant_id == order.tenant_id,
            ReturnRequest.status.in_(RESERVING_STATES),
        )).all()
        committed = {}
        for request in requests:
            for line in request.items:
                committed[line.order_item_id] = committed.get(line.order_item_id, 0) + line.quantity
        unified_cases = db.scalars(select(PostSaleCase).where(
            PostSaleCase.order_id == order.id,
            PostSaleCase.status.in_(("REQUESTED", "APPROVED", "RECEIVED", "INSPECTED", "AWAITING_SETTLEMENT", "COMPLETED")),
        )).all()
        for case in unified_cases:
            for line in case.items:
                if line.order_item_id is not None:
                    committed[line.order_item_id] = committed.get(line.order_item_id, 0) + line.quantity
        available = remaining_return_quantities(
            {item.id: item.quantity for item in items}, committed,
        )
        return by_id, committed, available

    @staticmethod
    def eligibility(db: Session, user: User, order_id: int):
        """Read-only customer-facing selection data for the future Flutter flow."""
        order = ReturnService._customer_order(db, user, order_id)
        by_id, committed, available = ReturnService._returnable_quantities(db, order)
        policy = return_policy_for_order(order)
        eligible_status = policy["eligible"]
        lines = [
            {
                "order_item_id": item.id,
                "product_variant_id": item.product_variant_id,
                "purchased_quantity": item.quantity,
                "already_requested_quantity": committed.get(item.id, 0),
                "available_quantity": available[item.id] if eligible_status else 0,
                "unit_price": item.unit_price,
                "subtotal": item.subtotal,
            }
            for item in sorted(by_id.values(), key=lambda value: value.id)
        ]
        return {
            "order_id": order.id,
            "order_code": order.order_code,
            "order_status": order.status,
            "can_request": eligible_status and any(line["available_quantity"] for line in lines),
            "reason": policy["reason"] if not eligible_status else (
                None if any(line["available_quantity"] for line in lines)
                else "Todas las unidades de la compra ya fueron solicitadas o devueltas."
            ),
            "delivered_at": policy["delivered_at"],
            "return_deadline": policy["return_deadline"],
            "return_window_days": policy["return_window_days"],
            "items": lines,
        }

    @staticmethod
    def create(db: Session, user: User, data):
        if not user.role or user.role.name != "CLIENTE":
            raise PermissionError("Solo clientes pueden solicitar devoluciones.")
        if len({x.order_item_id for x in data.items}) != len(data.items):
            raise ValueError("No repitas productos de la misma compra.")
        try:
            # Lock the order before counting previously requested/received units.
            # This serializes simultaneous requests for the same purchase.
            order = ReturnService._customer_order(db, user, data.order_id, lock=True)
            policy = return_policy_for_order(order)
            if not policy["eligible"]:
                raise ValueError(policy["reason"])
            by_id, committed, available = ReturnService._returnable_quantities(db, order)
            for line in data.items:
                if line.order_item_id not in by_id:
                    raise ValueError("Producto no pertenece a la compra.")
                if line.quantity > available[line.order_item_id]:
                    raise ValueError("Cantidad excede las unidades aún elegibles para devolver.")
            req = ReturnRequest(tenant_id=user.tenant_id, order_id=order.id, customer_id=user.id, reason=data.reason.strip(), status="REQUESTED")
            req.items = [ReturnItem(order_item_id=line.order_item_id, quantity=line.quantity) for line in data.items]
            db.add(req)
            db.commit()
            db.refresh(req)
            return req
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def list(db, user, mine=False):
        q = select(ReturnRequest).where(ReturnRequest.tenant_id == ReturnService._tenant(user))
        if mine or user.role.name == "CLIENTE":
            q = q.where(ReturnRequest.customer_id == user.id)
        else:
            q = ReturnService._staff_request_query(db, user)
        return db.scalars(q.order_by(ReturnRequest.id.desc()).limit(100)).all()

    @staticmethod
    def get(db, user, request_id):
        item = ReturnService._get(db, request_id, user)
        if user.role.name == "CLIENTE":
            if item.customer_id != user.id:
                raise LookupError("Solicitud no encontrada.")
        else:
            return ReturnService._require_staff_request(db, user, request_id)
        return item

    @staticmethod
    def change(db, user, request_id, action, note=None):
        ReturnService._staff(user)
        try:
            req = ReturnService._require_staff_request(db, user, request_id, lock=True)
            expected = "REQUESTED" if action in {"approve", "reject"} else "APPROVED"
            if req.status != expected:
                raise ValueError("Transición inválida para el estado actual.")
            req.status = {"approve":"APPROVED", "reject":"REJECTED", "receive":"RECEIVED"}[action]
            now = datetime.now(timezone.utc)
            if action in {"approve", "reject"}:
                req.reviewed_by = user.id
                req.reviewed_at = now
            else:
                req.received_by = user.id
                req.received_at = now
            req.admin_note = note.strip() if note else req.admin_note
            # FASE 1: no efectuar reembolsos ni reposiciones de inventario aquí.
            db.commit()
            db.refresh(req)
            return req
        except Exception:
            db.rollback()
            raise

    @staticmethod
    def cancel(db, user, request_id):
        try:
            req = ReturnService._get(db, request_id, user, lock=True)
            if req.customer_id != user.id or not user.role or user.role.name != "CLIENTE":
                raise PermissionError("No puedes cancelar esta solicitud.")
            if req.status != "REQUESTED":
                raise ValueError("Solo puedes cancelar solicitudes sin revisar.")
            req.status = "CANCELLED"
            db.commit()
            db.refresh(req)
            return req
        except Exception:
            db.rollback()
            raise
