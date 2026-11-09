"""Cobro de reserva: una transacción de venta + pago + consumo de stock reservado."""
from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session
from app.models.audit_log import AuditLog
from app.models.branch import Branch
from app.models.employee_branch import EmployeeBranch
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.payment import Payment
from app.models.reservation import Reservation
from app.models.reservation_item import ReservationItem
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User
from app.schemas.cash_payment import ReservationCheckoutCreate
from app.services.notification_service import NotificationService


def money(value):
    return Decimal(str(value or 0)).quantize(Decimal('0.01'))


class ReservationCheckoutService:
    @staticmethod
    def process(db: Session, *, reservation_id: int, current_user: User, data: ReservationCheckoutCreate):
        try:
            if not current_user.role or current_user.role.name != 'CAJERO':
                raise PermissionError('Solo un cajero puede cobrar reservas.')
            tenant_id = current_user.tenant_id
            if tenant_id is None:
                raise PermissionError('No se identificó la empresa activa.')

            reservation = (db.query(Reservation)
                .filter(Reservation.id == reservation_id, Reservation.tenant_id == tenant_id)
                .with_for_update(of=Reservation).first())
            if reservation is None:
                raise LookupError('Reserva no encontrada en esta empresa.')
            branch = db.query(Branch).filter(Branch.id == reservation.branch_id,
                Branch.tenant_id == tenant_id, Branch.is_active.is_(True)).first()
            if branch is None:
                raise PermissionError('La sucursal no pertenece a la empresa activa.')
            assignment = db.query(EmployeeBranch).filter(
                EmployeeBranch.user_id == current_user.id,
                EmployeeBranch.branch_id == reservation.branch_id,
                EmployeeBranch.is_active.is_(True)).first()
            if assignment is None:
                raise PermissionError('El cajero no está asignado a la sucursal de retiro.')
            if db.query(Sale.id).filter(Sale.reservation_id == reservation.id).first():
                raise ValueError('Esta reserva ya tiene una venta vinculada. No se puede cobrar otra vez.')
            if reservation.status != 'ATTENDED':
                raise ValueError('La reserva debe estar ATENDIDA antes de cobrarla.')

            items = (db.query(ReservationItem).filter(ReservationItem.reservation_id == reservation.id)
                .order_by(ReservationItem.product_variant_id).all())
            if not items or any(item.status != 'RESERVED' for item in items):
                raise ValueError('La reserva no tiene todas sus prendas apartadas.')
            variant_ids = [item.product_variant_id for item in items]
            inventory_rows = (db.query(Inventory).filter(
                Inventory.branch_id == reservation.branch_id,
                Inventory.product_variant_id.in_(variant_ids),
                Inventory.is_active.is_(True)).order_by(Inventory.id).with_for_update().all())
            inventories = {row.product_variant_id: row for row in inventory_rows}
            for item in items:
                inventory = inventories.get(item.product_variant_id)
                if inventory is None or inventory.stock_quantity < item.quantity or inventory.reserved_quantity < item.quantity:
                    raise ValueError(f'Stock reservado insuficiente para la variante {item.product_variant_id}.')

            total = money(sum(money(i.unit_price) * i.quantity for i in items))
            if total <= 0:
                raise ValueError('El total de la venta debe ser mayor que cero.')
            received = None
            change = money(0)
            if data.payment_method == 'CASH':
                if data.amount_received is None:
                    raise ValueError('Debes indicar el monto recibido en efectivo.')
                received = money(data.amount_received)
                if received < total:
                    raise ValueError('El importe recibido no cubre el total.')
                change = money(received - total)

            now = datetime.now(timezone.utc)
            sale = Sale(tenant_id=tenant_id, reservation_id=reservation.id,
                sale_code=f'SALE-{now:%Y%m%d}-{uuid4().hex[:10].upper()}',
                branch_id=reservation.branch_id, cashier_id=current_user.id,
                customer_id=reservation.customer_id, status='PAID', subtotal=total,
                discount_amount=money(0), total_amount=total)
            db.add(sale)
            db.flush()
            for item in items:
                db.add(SaleItem(sale_id=sale.id, product_variant_id=item.product_variant_id,
                    quantity=item.quantity, unit_price=item.unit_price,
                    subtotal=money(item.unit_price * item.quantity)))
                inv = inventories[item.product_variant_id]
                stock_before, reserved_before = inv.stock_quantity, inv.reserved_quantity
                inv.stock_quantity -= item.quantity
                inv.reserved_quantity -= item.quantity
                item.status = 'CONSUMED'
                db.add(InventoryMovement(inventory_id=inv.id, movement_type='SALE',
                    quantity=item.quantity, stock_before=stock_before,
                    stock_after=inv.stock_quantity, reserved_before=reserved_before,
                    reserved_after=inv.reserved_quantity, user_id=current_user.id,
                    reference_type='SALE', reference_id=sale.id,
                    reference_code=sale.sale_code, reason=f'Cobro de reserva {reservation.reservation_code}'))

            payment = Payment(payment_code=f'PAY-{now:%Y%m%d}-{uuid4().hex[:10].upper()}',
                sale_id=sale.id, order_id=None, user_id=current_user.id,
                payment_method=data.payment_method, channel='CASH_DESK',
                provider=data.provider, amount=total, currency='BOB', status='APPROVED',
                external_transaction_id=data.external_transaction_id,
                external_reference=data.external_reference, paid_at=now)
            db.add(payment)
            db.flush()
            reservation.status = 'COMPLETED'
            reservation.completed_at = now
            db.add(AuditLog(user_id=current_user.id, action='PAY', module='SALES',
                entity_type='Sale', entity_id=sale.id,
                description=f'Cobro de reserva {reservation.reservation_code} con venta {sale.sale_code}.',
                old_values={'reservation_status': 'ATTENDED'},
                new_values={'reservation_status': 'COMPLETED', 'payment_id': payment.id,
                    'sale_id': sale.id, 'reservation_id': reservation.id}, status='SUCCESS'))
            NotificationService.notify_reservation_status(db, reservation=reservation, status='COMPLETED')
            db.commit()
            return dict(reservation_id=reservation.id, reservation_code=reservation.reservation_code,
                sale_id=sale.id, sale_code=sale.sale_code, payment_id=payment.id,
                payment_code=payment.payment_code, amount=total,
                change_amount=change, status='COMPLETED')
        except Exception:
            db.rollback()
            raise
