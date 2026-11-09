"""Solicitud y tramitación POS sin transferir fondos automáticamente.

La confirmación financiera registra una declaración administrativa, NO ejecuta pagos.
"""
import os
from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from sqlalchemy import select, func
from sqlalchemy.orm import Session
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.sale_return import SaleReturn, SaleReturnItem
from app.models.payment import Payment
from app.models.employee_branch import EmployeeBranch
from app.models.branch import Branch
from app.models.user import User
from app.models.post_sale_case import PostSaleCase, PostSaleSettlement
from app.models.sale_exchange import SaleExchange

ACTIVE = ('REQUESTED','APPROVED','RECEIVED','INSPECTED','REFUNDED')
STAFF = ('TENANT_ADMIN','ADMINISTRADOR','ENCARGADO_SUCURSAL')
ADMIN = ('TENANT_ADMIN','ADMINISTRADOR')

def _now(): return datetime.now(timezone.utc)
def _money(v): return Decimal(v).quantize(Decimal('0.01'),rounding=ROUND_HALF_UP)

class SaleReturnService:
    @staticmethod
    def _role(user): return user.role.name if user.role else ''

    @classmethod
    def _staff_access(cls, db, user, record):
        if cls._role(user) not in STAFF or user.tenant_id is None or record.tenant_id != user.tenant_id:
            raise PermissionError('Sin permiso para gestionar esta devolución.')
        if cls._role(user) == 'ENCARGADO_SUCURSAL':
            found = db.scalar(select(EmployeeBranch.id).join(Branch,Branch.id==EmployeeBranch.branch_id).where(
                EmployeeBranch.user_id==user.id, EmployeeBranch.branch_id==record.branch_id,
                EmployeeBranch.is_active.is_(True), Branch.is_active.is_(True), Branch.tenant_id==user.tenant_id))
            if found is None: raise PermissionError('La devolución pertenece a otra sucursal.')

    @classmethod
    def _visible(cls, db, user, record):
        if cls._role(user)=='CLIENTE':
            if record.customer_id != user.id or record.tenant_id != user.tenant_id:
                raise LookupError('Devolución no encontrada.')
        else: cls._staff_access(db,user,record)

    @staticmethod
    def _get(db, rid, lock=False):
        q=select(SaleReturn).where(SaleReturn.id==rid)
        if lock: q=q.with_for_update()
        r=db.scalar(q)
        if r is None: raise LookupError('Devolución no encontrada.')
        return r

    @staticmethod
    def _dump(r):
        return {'id':r.id,'sale_id':r.sale_id,'customer_id':r.customer_id,'tenant_id':r.tenant_id,
                'branch_id':r.branch_id,'status':r.status,'reason':r.reason,'staff_note':r.staff_note,
                'requested_amount':r.requested_amount,'currency':'BOB','created_at':r.created_at,
                'reviewed_at':r.reviewed_at,'received_at':r.received_at,'inspected_at':r.inspected_at,
                'refunded_at':r.refunded_at,'refund_mode':r.refund_mode,'refund_reference':r.refund_reference,
                'items':[{'sale_item_id':i.sale_item_id,'quantity':i.quantity,'condition':i.condition} for i in r.items]}

    @classmethod
    def eligibility(cls, db, user, sale_id):
        if cls._role(user)!='CLIENTE': raise PermissionError('Solo clientes pueden solicitar devoluciones.')
        s=db.scalar(select(Sale).where(Sale.id==sale_id,Sale.customer_id==user.id,Sale.tenant_id==user.tenant_id))
        if s is None: raise LookupError('Compra presencial no encontrada.')
        items=db.scalars(select(SaleItem).where(SaleItem.sale_id==s.id)).all()
        used={}
        rs=db.scalars(select(SaleReturn).where(SaleReturn.sale_id==s.id,SaleReturn.status.in_(ACTIVE))).all()
        for r in rs:
            for i in r.items:used[i.sale_item_id]=used.get(i.sale_item_id,0)+i.quantity
        legacy_exchanges=db.scalars(select(SaleExchange).where(SaleExchange.sale_id==s.id)).all()
        for exchange in legacy_exchanges:
            used[exchange.sale_item_id]=used.get(exchange.sale_item_id,0)+exchange.quantity
        unified_cases=db.scalars(select(PostSaleCase).where(
            PostSaleCase.sale_id==s.id,
            PostSaleCase.status.in_(("REQUESTED","APPROVED","RECEIVED","INSPECTED","AWAITING_SETTLEMENT","COMPLETED"))
        )).all()
        for case in unified_cases:
            for item in case.items:
                if item.sale_item_id is not None:
                    used[item.sale_item_id]=used.get(item.sale_item_id,0)+item.quantity
        # Política: 7 días desde la venta pagada; comprobar fecha y estado.
        created=s.created_at
        if created and created.tzinfo is None:created=created.replace(tzinfo=timezone.utc)
        deadline=created+timedelta(days=7) if created else None
        eligible=s.status=='PAID' and bool(deadline) and created<=_now()<deadline
        approved_payment=db.scalar(select(Payment.id).where(Payment.sale_id==s.id, Payment.status=='APPROVED'))
        eligible=eligible and approved_payment is not None
        lines=[{'sale_item_id':i.id,'product_variant_id':i.product_variant_id,
                'purchased_quantity':i.quantity,'available_quantity':max(0,i.quantity-used.get(i.id,0)) if eligible else 0,
                'unit_price':i.unit_price} for i in items]
        reason=None if eligible else 'La venta debe estar pagada, tener un pago aprobado y estar dentro de los 7 días.'
        return {'sale_id':s.id,'sale_code':s.sale_code,'branch_id':s.branch_id,'eligible':eligible and any(x['available_quantity'] for x in lines),
                'deadline':deadline,'reason':reason,'items':lines}

    @classmethod
    def create(cls,db,user,data):
        # Lock serializes concurrent requests against the same sale.
        s=db.scalar(select(Sale).where(Sale.id==data.sale_id,Sale.customer_id==user.id,Sale.tenant_id==user.tenant_id).with_for_update())
        if s is None or cls._role(user)!='CLIENTE': raise LookupError('Venta no encontrada para tu cuenta.')
        eligibility=cls.eligibility(db,user,s.id)
        if not eligibility['eligible']: raise ValueError(eligibility['reason'] or 'No quedan unidades para devolver.')
        ids=[i.sale_item_id for i in data.items]
        if len(ids)!=len(set(ids)):raise ValueError('No repitas artículos.')
        by_id={i['sale_item_id']:i for i in eligibility['items']}
        amount=Decimal('0')
        for i in data.items:
            if i.sale_item_id not in by_id or i.quantity>by_id[i.sale_item_id]['available_quantity']:
                raise ValueError('Cantidad inválida o ya solicitada.')
            amount+=_money(by_id[i.sale_item_id]['unit_price'])*i.quantity
        # Prorratear el descuento del ticket evita reembolsar más de lo cobrado.
        if s.subtotal and s.subtotal>0:
            amount=_money(amount*Decimal(s.total_amount)/Decimal(s.subtotal))
        r=SaleReturn(tenant_id=s.tenant_id,branch_id=s.branch_id,sale_id=s.id,customer_id=user.id,
                     reason=data.reason.strip(),requested_amount=amount)
        r.items=[SaleReturnItem(sale_item_id=i.sale_item_id,quantity=i.quantity) for i in data.items]
        db.add(r);db.commit();db.refresh(r)
        return cls._dump(r)

    @classmethod
    def list(cls,db,user):
        role=cls._role(user)
        q=select(SaleReturn)
        if role=='CLIENTE':q=q.where(SaleReturn.customer_id==user.id,SaleReturn.tenant_id==user.tenant_id)
        elif role in STAFF:
            q=q.where(SaleReturn.tenant_id==user.tenant_id)
            if role=='ENCARGADO_SUCURSAL':
                q=q.where(SaleReturn.branch_id.in_(select(EmployeeBranch.branch_id).join(Branch,Branch.id==EmployeeBranch.branch_id).where(
                    EmployeeBranch.user_id==user.id,EmployeeBranch.is_active.is_(True),Branch.is_active.is_(True),Branch.tenant_id==user.tenant_id)))
        else:raise PermissionError('No tienes acceso a devoluciones.')
        return [cls._dump(r) for r in db.scalars(q.order_by(SaleReturn.id.desc()).limit(100)).all()]

    @classmethod
    def detail(cls,db,user,rid):
        r=cls._get(db,rid);cls._visible(db,user,r);return cls._dump(r)

    @classmethod
    def decide(cls,db,user,rid,data):
        r=cls._get(db,rid,True);cls._staff_access(db,user,r)
        if r.status!='REQUESTED':raise ValueError('La solicitud ya fue revisada.')
        r.status='APPROVED' if data.approve else 'REJECTED';r.staff_note=data.note
        r.reviewed_by=user.id;r.reviewed_at=_now()
        db.commit();db.refresh(r);return cls._dump(r)

    @classmethod
    def receive(cls,db,user,rid):
        r=cls._get(db,rid,True);cls._staff_access(db,user,r)
        if r.status!='APPROVED':raise ValueError('Solo pueden recibirse devoluciones aprobadas.')
        r.status='RECEIVED';r.received_by=user.id;r.received_at=_now()
        db.commit();db.refresh(r);return cls._dump(r)

    @classmethod
    def inspect(cls,db,user,rid,data):
        r=cls._get(db,rid,True);cls._staff_access(db,user,r)
        if r.status!='RECEIVED':raise ValueError('Primero recibe la devolución en sucursal.')
        supplied={x.sale_item_id:x.condition for x in data.items}
        if len(supplied)!=len(data.items) or set(supplied)!={i.sale_item_id for i in r.items}:
            raise ValueError('Debes inspeccionar cada artículo de la solicitud exactamente una vez.')
        for i in r.items:i.condition=supplied[i.sale_item_id]
        r.status='INSPECTED';r.inspected_by=user.id;r.inspected_at=_now()
        # No modificar inventario hasta habilitar el flujo de recepción física auditada.
        db.commit();db.refresh(r);return cls._dump(r)

    @classmethod
    def refund(cls,db,user,rid,data):
        if cls._role(user) not in ADMIN:raise PermissionError('Solo el administrador confirma reembolsos.')
        r=cls._get(db,rid,True);cls._staff_access(db,user,r)
        if r.status!='INSPECTED':raise ValueError('Primero deben recibirse e inspeccionarse los artículos.')
        s=db.scalar(select(Sale).where(Sale.id==r.sale_id))
        payments=db.scalars(select(Payment).where(Payment.sale_id==s.id,Payment.status=='APPROVED')).all()
        if not payments:raise ValueError('No hay un pago aprobado para esta venta.')
        if data.mode=='DEMO':
            if os.getenv('FASHIONSTORE_ENABLE_DEMO_REFUNDS','').lower()!='true':
                raise PermissionError('Reembolsos demo deshabilitados en este entorno.')
            if any((p.provider or '').upper() != 'DEMO_LOCAL' for p in payments):
                raise ValueError('Solo los pagos identificados explícitamente como DEMO_LOCAL admiten reembolso simulado.')
            reference=f'DEMO-POS-RETURN-{r.id}'
        else:
            if not data.reference or len(data.reference.strip())<6:
                raise ValueError('Se requiere constancia externa de devolución de dinero (6 caracteres mínimo).')
            reference=data.reference.strip()
        # Evitar que los reintegros anteriores del flujo unificado excedan lo cobrado.
        unified_refunds=db.scalar(select(func.coalesce(func.sum(PostSaleSettlement.amount),0))
            .join(PostSaleCase,PostSaleCase.id==PostSaleSettlement.case_id)
            .where(PostSaleCase.sale_id==s.id,PostSaleSettlement.kind=='REFUND',
                   PostSaleSettlement.status.in_(('PROCESSING','COMPLETED','MANUAL_REVIEW'))))
        previous_legacy=db.scalar(select(func.coalesce(func.sum(SaleReturn.requested_amount),0)).where(
            SaleReturn.sale_id==s.id,SaleReturn.status=='REFUNDED',SaleReturn.id!=r.id))
        paid_total=sum((Decimal(p.amount) for p in payments),Decimal('0'))
        refund_cap=min(paid_total,Decimal(s.total_amount))
        if Decimal(unified_refunds or 0)+Decimal(previous_legacy or 0)+r.requested_amount>refund_cap:
            raise ValueError('El reintegro acumulado superaría el importe neto cobrado.')
        # EXTERNAL_MANUAL es una declaración del administrador, no transferencia ni conciliación.
        r.status='REFUNDED';r.refund_mode=data.mode;r.refund_reference=reference
        r.refunded_by=user.id;r.refunded_at=_now()
        db.commit();db.refresh(r);return cls._dump(r)
