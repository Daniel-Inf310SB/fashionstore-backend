"""CU77 - cambio presencial atómico (solo prendas aptas y efectivo).

Diferencias a favor NO se convierten automáticamente en crédito; requieren
el futuro submódulo de saldos por tenant.
"""
from decimal import Decimal
from uuid import UUID, uuid4
from sqlalchemy.orm import Session
from app.models.sale import Sale
from app.models.sale_exchange import SaleExchange
from app.models.sale_return import SaleReturn
from app.models.post_sale_case import PostSaleCase
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.services.sale_exchange_quote_service import quote, _load_sale, money
from app.services.sale_service import SaleService


def _result(ex: SaleExchange):
    return {'id': ex.id, 'exchange_code': ex.exchange_code, 'sale_id': ex.sale_id,
            'sale_item_id': ex.sale_item_id, 'original_variant_id': ex.original_variant_id,
            'replacement_variant_id': ex.replacement_variant_id, 'quantity': ex.quantity,
            'original_paid_total': ex.original_paid_total, 'replacement_total': ex.replacement_total,
            'additional_paid': ex.additional_paid, 'payment_method': ex.payment_method,
            'created_at': ex.created_at, 'status': 'COMPLETED'}


def history(db: Session, user, sale_id: int):
    sale = SaleService._get(db, sale_id)
    SaleService._check_access(db, sale, user)
    return [_result(x) for x in db.query(SaleExchange).filter(
        SaleExchange.sale_id == sale_id).order_by(SaleExchange.id).all()]


def confirm(db: Session, user, sale_id: int, *, client_operation_id: str,
            sale_item_id: int, replacement_variant_id: int, quantity: int,
            item_condition: str, amount_received: Decimal, expected_additional: Decimal):
    raise ValueError(
        "La confirmación directa de cambios fue sustituida por el flujo unificado "
        "POST /post-sale/cases. Registra solicitud, aprobación, recepción, inspección y liquidación."
    )
    try:
        uuid = str(UUID(client_operation_id))
    except (ValueError, AttributeError) as exc:
        raise ValueError('UUID inválido para identificar el cambio.') from exc
    # Bloquear la venta serializa los cambios parciales de una misma venta.
    try:
        sale = db.query(Sale).filter(Sale.id == sale_id).with_for_update().first()
        if sale is None:
            raise LookupError('La venta no existe.')
        SaleService._check_access(db, sale, user)
        existing = db.query(SaleExchange).filter(SaleExchange.client_operation_id == uuid).first()
        if existing is not None:
            if (existing.sale_id,existing.sale_item_id,existing.replacement_variant_id,
                existing.quantity,existing.item_condition) != (sale_id,sale_item_id,replacement_variant_id,quantity,item_condition) or \
               money(existing.additional_paid) != money(amount_received) or \
               money(existing.additional_paid) != money(expected_additional):
                raise ValueError('El UUID ya se utilizó con otros datos.')
            db.rollback()
            return _result(existing)
        _load_sale(db, user, sale_id)
        if item_condition != 'RESELLABLE':
            raise ValueError('Solo se permite reingresar prendas inspeccionadas y aptas para reventa.')
        if quantity < 1:
            raise ValueError('La cantidad debe ser positiva.')
        past = db.query(SaleExchange).filter(SaleExchange.sale_item_id == sale_item_id).all()
        legacy_returns = db.query(SaleReturn).filter(
            SaleReturn.sale_id == sale_id,
            SaleReturn.status.in_(("REQUESTED", "APPROVED", "RECEIVED", "INSPECTED", "REFUNDED")),
        ).all()
        returned_qty = sum(
            item.quantity for request in legacy_returns for item in request.items
            if item.sale_item_id == sale_item_id
        )
        unified_cases = db.query(PostSaleCase).filter(
            PostSaleCase.sale_id == sale_id,
            PostSaleCase.status.in_(("REQUESTED", "APPROVED", "RECEIVED", "INSPECTED", "AWAITING_SETTLEMENT", "COMPLETED")),
        ).all()
        unified_qty = sum(
            item.quantity for case in unified_cases for item in case.items
            if item.sale_item_id == sale_item_id
        )
        line = next((i for i in sale.items if i.id == sale_item_id),None)
        if line is None or sum(x.quantity for x in past) + returned_qty + unified_qty + quantity > line.quantity:
            raise ValueError('La cantidad supera las unidades pendientes de cambio o devolución.')
        data = quote(db,user,sale_id,sale_item_id,replacement_variant_id,quantity)
        delta = money(data['additional_to_collect'])
        if money(data['potential_store_credit']) > 0:
            raise ValueError('Los cambios con crédito a favor aún no están habilitados; no se modificó inventario.')
        if money(expected_additional) != delta:
            raise ValueError('La cotización cambió. Vuelve a cotizar antes de confirmar.')
        if money(amount_received) != delta:
            raise ValueError('Registra el monto exacto de la diferencia en efectivo; el vuelto no se gestiona en este flujo.')
        # Bloquear los inventarios en orden estable para evitar deadlocks.
        ids = sorted([line.product_variant_id,replacement_variant_id])
        locked = (db.query(Inventory).filter(Inventory.branch_id==sale.branch_id,
                  Inventory.product_variant_id.in_(ids),Inventory.is_active.is_(True))
                  .order_by(Inventory.product_variant_id).with_for_update().all())
        by_variant = {i.product_variant_id:i for i in locked}
        if any(i not in by_variant for i in ids):
            raise ValueError('No existe inventario activo de alguna de las variantes.')
        outgoing=by_variant[replacement_variant_id]; returned=by_variant[line.product_variant_id]
        if outgoing.stock_quantity-outgoing.reserved_quantity < quantity:
            raise ValueError('Stock insuficiente tras la actualización concurrente.')
        ex = SaleExchange(client_operation_id=uuid,exchange_code='EXC-'+uuid4().hex[:18].upper(),
             tenant_id=sale.tenant_id,sale_id=sale.id,sale_item_id=line.id,
             branch_id=sale.branch_id,cashier_id=user.id,original_variant_id=line.product_variant_id,
             replacement_variant_id=replacement_variant_id,quantity=quantity,
             original_paid_total=data['original_paid_total_estimate'],replacement_total=data['replacement_total'],
             additional_paid=delta,payment_method='CASH' if delta>0 else None,item_condition=item_condition)
        db.add(ex);db.flush()
        for inv, direction in ((returned,1),(outgoing,-1)):
            before=inv.stock_quantity;reserved=inv.reserved_quantity
            inv.stock_quantity=before+direction*quantity
            db.add(InventoryMovement(inventory_id=inv.id,movement_type='RETURN_IN' if direction==1 else 'RETURN_OUT',
                quantity=quantity,stock_before=before,stock_after=inv.stock_quantity,
                reserved_before=reserved,reserved_after=reserved,user_id=user.id,
                reference_type='SALE_EXCHANGE',reference_id=ex.id,reference_code=ex.exchange_code,
                reason='Cambio de prenda CU77',notes='Efectivo adicional recibido y confirmado en caja' if delta>0 else 'Sin diferencia'))
        db.commit();db.refresh(ex)
        return _result(ex)
    except Exception:
        db.rollback()
        raise
