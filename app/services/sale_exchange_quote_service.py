"""CU77: consultas y cotizaciones de cambios, SIN mutar venta, pagos o inventario.

Esta etapa es de prevalidación. La confirmación transaccional requiere un
registro de cambios y conciliación de pagos/créditos; nunca se simula aquí.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy.orm import Session
from app.models.inventory import Inventory
from app.models.product_variant import ProductVariant
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User
from app.services.sale_service import SaleService

CENT = Decimal("0.01")
CHANGE_WINDOW_DAYS = 7


def money(value) -> Decimal:
    return Decimal(str(value or 0)).quantize(CENT, rounding=ROUND_HALF_UP)


def paid_unit_amount(sale: Sale, line: SaleItem) -> Decimal:
    """Valor neto proporcional de una unidad, incluyendo descuento original.

    Para una venta con múltiples líneas, se redondea la cotización de cada
    prenda. La conciliación de centavos debe cerrarse en la confirmación final.
    """
    gross = money(sale.subtotal)
    if gross <= 0:
        raise ValueError("La venta no tiene un subtotal válido.")
    net = money(sale.total_amount)
    return money(Decimal(str(line.unit_price)) * net / gross)


def _load_sale(db: Session, current_user: User, sale_id: int) -> Sale:
    sale = SaleService._get(db, sale_id)
    SaleService._check_access(db, sale, current_user)
    if sale.status != "PAID":
        raise ValueError("Solo se permiten cambios sobre ventas pagadas.")
    now = datetime.now(timezone.utc)
    created = sale.created_at
    if created.tzinfo is None:
        created = created.replace(tzinfo=timezone.utc)
    if created > now or now > created + timedelta(days=CHANGE_WINDOW_DAYS):
        raise ValueError("La venta está fuera del plazo de 7 días para cambios.")
    if not sale.receipt:
        raise ValueError("La venta no tiene un comprobante emitido.")
    return sale


def eligibility(db: Session, current_user: User, sale_id: int) -> dict:
    sale = _load_sale(db, current_user, sale_id)
    return {
        "sale_id": sale.id,
        "sale_code": sale.sale_code,
        "receipt_number": sale.receipt.receipt_number,
        "status": sale.status,
        "branch_id": sale.branch_id,
        "change_window_days": CHANGE_WINDOW_DAYS,
        "deadline": (sale.created_at.replace(tzinfo=timezone.utc)
                     if sale.created_at.tzinfo is None else sale.created_at)
                    + timedelta(days=CHANGE_WINDOW_DAYS),
        "items": [{
            "sale_item_id": line.id,
            "product_variant_id": line.product_variant_id,
            "quantity_purchased": line.quantity,
            "original_unit_price": money(line.unit_price),
            "paid_unit_price_estimate": paid_unit_amount(sale, line),
        } for line in sale.items],
    }


def quote(db: Session, current_user: User, sale_id: int,
          sale_item_id: int, replacement_variant_id: int, quantity: int) -> dict:
    sale = _load_sale(db, current_user, sale_id)
    line = next((x for x in sale.items if x.id == sale_item_id), None)
    if line is None:
        raise LookupError("La prenda no pertenece a la venta indicada.")
    if quantity < 1 or quantity > line.quantity:
        raise ValueError("La cantidad a cambiar supera las unidades de la venta.")
    if replacement_variant_id == line.product_variant_id:
        raise ValueError("Selecciona una variante de reemplazo distinta.")

    variant = db.query(ProductVariant).filter(
        ProductVariant.id == replacement_variant_id
    ).first()
    if variant is None or not variant.is_active or variant.product is None or not variant.product.is_active:
        raise LookupError("La variante de reemplazo no existe o está inactiva.")
    if variant.product.tenant_id != sale.tenant_id:
        raise PermissionError("La variante pertenece a otra empresa.")
    inventory = db.query(Inventory).filter(
        Inventory.branch_id == sale.branch_id,
        Inventory.product_variant_id == replacement_variant_id,
        Inventory.is_active.is_(True),
    ).first()
    if inventory is None or inventory.available_quantity < quantity:
        raise ValueError("Stock insuficiente para la prenda de reemplazo.")

    old_unit = paid_unit_amount(sale, line)
    new_unit = money(Decimal(str(variant.product.base_price)) + Decimal(str(variant.additional_price)))
    amount_paid = money(old_unit * quantity)
    amount_new = money(new_unit * quantity)
    delta = money(amount_new - amount_paid)
    return {
        "sale_id": sale.id,
        "sale_item_id": line.id,
        "original_variant_id": line.product_variant_id,
        "replacement_variant_id": variant.id,
        "quantity": quantity,
        "original_paid_unit_price_estimate": old_unit,
        "replacement_unit_price": new_unit,
        "original_paid_total_estimate": amount_paid,
        "replacement_total": amount_new,
        "additional_to_collect": max(delta, Decimal("0.00")),
        "potential_store_credit": max(-delta, Decimal("0.00")),
        "available_replacement_stock": inventory.available_quantity,
        "is_finalized": False,
        "message": "Cotización preliminar: no se modificaron ventas, pagos ni inventario.",
    }
