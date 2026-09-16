from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy.orm import Session, joinedload
from app.models.audit_log import AuditLog
from app.models.payment import Payment
from app.models.product_variant import ProductVariant
from app.models.receipt import Receipt
from app.models.receipt_item import ReceiptItem
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User

class ReceiptService:
    @staticmethod
    def issue_sale_receipt(db:Session,*,current_user:User,sale_id:int):
        if current_user.role is None or current_user.role.name!='CAJERO': raise PermissionError('Solo un cajero puede emitir el comprobante de una venta presencial.')
        sale=db.query(Sale).options(joinedload(Sale.customer),joinedload(Sale.items).joinedload(SaleItem.product_variant).joinedload(ProductVariant.product),joinedload(Sale.items).joinedload(SaleItem.product_variant).joinedload(ProductVariant.size),joinedload(Sale.items).joinedload(SaleItem.product_variant).joinedload(ProductVariant.color),joinedload(Sale.payments),joinedload(Sale.receipt)).filter(Sale.id==sale_id).first()
        if sale is None: raise LookupError('La venta presencial no existe.')
        if sale.cashier_id!=current_user.id: raise PermissionError('No puedes emitir el comprobante de una venta de otro cajero.')
        if sale.status!='PAID': raise ValueError('Solo se puede emitir comprobante para una venta pagada.')
        if sale.receipt is not None: return sale.receipt
        payment=next((p for p in sorted(sale.payments,key=lambda x:x.id,reverse=True) if p.status=='APPROVED'),None)
        if payment is None: raise ValueError('La venta no tiene un pago aprobado.')
        c=sale.customer; name='CONSUMIDOR FINAL' if c is None else f'{c.first_name} {c.last_name or ""}'.strip()
        r=Receipt(receipt_number=f'REC-{datetime.now(timezone.utc).strftime("%Y%m%d")}-{uuid4().hex[:10].upper()}',receipt_type='IN_STORE_SALE',order_id=None,sale_id=sale.id,customer_name=name,customer_email=c.email if c else None,customer_document=c.document_number if c else None,subtotal=sale.subtotal,discount_amount=sale.discount_amount,total_amount=sale.total_amount,payment_method=payment.payment_method,currency=payment.currency,email_status='NOT_REQUESTED')
        db.add(r); db.flush()
        for item in sale.items:
            v=item.product_variant
            db.add(ReceiptItem(receipt_id=r.id,product_name=v.product.name,sku=v.sku,size_name=v.size.name if v.size else None,color_name=v.color.name if v.color else None,quantity=item.quantity,unit_price=item.unit_price,subtotal=item.subtotal))
        db.add(AuditLog(user_id=current_user.id,action='CREATE',module='RECEIPTS',entity_type='Receipt',entity_id=r.id,description=f'Comprobante {r.receipt_number} emitido para {sale.sale_code}.',old_values=None,new_values={'sale_id':sale.id,'total_amount':str(r.total_amount)},status='SUCCESS'))
        db.commit()
        return db.query(Receipt).options(joinedload(Receipt.items)).filter(Receipt.id==r.id).first()
    @staticmethod
    def get_by_sale(db:Session,*,current_user:User,sale_id:int):
        r=db.query(Receipt).options(joinedload(Receipt.items),joinedload(Receipt.sale)).filter(Receipt.sale_id==sale_id).first()
        if r is None: raise LookupError('La venta todavía no tiene comprobante.')
        if current_user.role is None: raise PermissionError('Usuario sin rol.')
        if current_user.role.name=='ADMINISTRADOR': return r
        if current_user.role.name=='CAJERO' and r.sale.cashier_id==current_user.id: return r
        raise PermissionError('No puedes consultar este comprobante.')
