from sqlalchemy import select
from sqlalchemy.orm import Session
from app.models.return_request import ReturnRequest, ReturnItem
from app.models.return_refund import ReturnRefund
from app.models.return_inspection import ReturnInspection
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.branch import Branch
from app.models.product_variant import ProductVariant
from app.models.product import Product
from app.services.return_service import ReturnService


class ReturnInspectionService:
    @staticmethod
    def _load_return(db: Session, user, return_id: int, lock=False):
        ret = ReturnService._require_staff_request(db, user, return_id, lock=lock)
        if ret.status != 'RECEIVED':
            raise ValueError('Primero debe registrarse la recepción de la devolución.')
        return ret

    @staticmethod
    def list_lines(db: Session, user, return_id: int):
        ret = ReturnInspectionService._load_return(db, user, return_id)
        order = db.get(Order, ret.order_id)
        if order is None or order.tenant_id != ret.tenant_id:
            raise ValueError('Pedido no coincide con la empresa.')
        result = []
        for line in ret.items:
            item = db.get(OrderItem, line.order_item_id)
            if item is None or item.order_id != order.id:
                raise ValueError('Artículo de devolución inconsistente.')
            inspected = db.scalar(select(ReturnInspection).where(ReturnInspection.return_item_id == line.id))
            result.append({
                'return_item_id': line.id,
                'order_item_id': item.id,
                'product_variant_id': item.product_variant_id,
                'branch_id': order.branch_id,
                'quantity': line.quantity,
                'decision': inspected.decision if inspected else 'PENDING',
                'movement_id': inspected.movement_id if inspected else None,
            })
        return result

    @staticmethod
    def decide(db: Session, user, return_id: int, return_item_id: int, data):
        try:
            ret = ReturnInspectionService._load_return(db, user, return_id, lock=True)
            line = db.scalar(select(ReturnItem).where(
                ReturnItem.id == return_item_id, ReturnItem.return_request_id == ret.id,
            ).with_for_update())
            if line is None:
                raise LookupError('Artículo no pertenece a esta devolución.')
            existing = db.scalar(select(ReturnInspection).where(
                ReturnInspection.return_item_id == line.id,
            ).with_for_update())
            if existing is not None:
                raise ValueError('Artículo ya inspeccionado. No se puede registrar dos veces.')
            refund = db.scalar(select(ReturnRefund).where(ReturnRefund.return_request_id == ret.id))
            if refund is None or refund.status != 'SUCCEEDED':
                raise ValueError('Se requiere reembolso confirmado antes de cerrar la inspección.')
            order = db.scalar(select(Order).where(
                Order.id == ret.order_id, Order.tenant_id == ret.tenant_id,
            ).with_for_update())
            if order is None:
                raise ValueError('Pedido inconsistente.')
            branch = db.get(Branch, order.branch_id)
            if branch is None or branch.tenant_id != ret.tenant_id:
                raise ValueError('Sucursal no pertenece a la empresa.')
            ordered = db.get(OrderItem, line.order_item_id)
            if ordered is None or ordered.order_id != order.id or line.quantity > ordered.quantity:
                raise ValueError('Artículo o cantidad no coincide con el pedido.')
            variant = db.get(ProductVariant, ordered.product_variant_id)
            product = db.get(Product, variant.product_id) if variant else None
            if product is None or product.tenant_id != ret.tenant_id:
                raise ValueError('Producto no pertenece a la empresa.')
            movement_id = None
            decision = 'RESTOCKED' if data.decision == 'RESTOCK' else 'DAMAGED'
            if decision == 'RESTOCKED':
                inventory = db.scalar(select(Inventory).where(
                    Inventory.branch_id == branch.id,
                    Inventory.product_variant_id == variant.id,
                ).with_for_update())
                if inventory is None or not inventory.is_active:
                    raise ValueError('No existe inventario activo para esta variante y sucursal. Revisar manualmente.')
                before = inventory.stock_quantity
                reserved = inventory.reserved_quantity
                after = before + line.quantity
                if inventory.maximum_stock is not None and after > inventory.maximum_stock:
                    raise ValueError('La reposición supera el stock máximo configurado.')
                inventory.stock_quantity = after
                movement = InventoryMovement(
                    inventory_id=inventory.id,
                    movement_type='RETURN_IN', quantity=line.quantity,
                    stock_before=before, stock_after=after,
                    reserved_before=reserved, reserved_after=reserved,
                    user_id=user.id, reference_type='RETURN_ITEM', reference_id=line.id,
                    reference_code=f'RETURN-{ret.id}-ITEM-{line.id}',
                    reason='Reposición de devolución inspeccionada', notes=data.note,
                )
                db.add(movement)
                db.flush()
                movement_id = movement.id
            inspection = ReturnInspection(
                return_item_id=line.id, tenant_id=ret.tenant_id, inspector_id=user.id,
                decision=decision, note=data.note, movement_id=movement_id,
            )
            db.add(inspection)
            db.commit()
            db.refresh(inspection)
            return inspection
        except Exception:
            db.rollback()
            raise
