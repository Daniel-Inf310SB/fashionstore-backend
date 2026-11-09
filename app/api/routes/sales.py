from datetime import datetime
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Path,Query,status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.sales import require_sales_cancel, require_sales_create, require_sales_view
from app.models.user import User
from app.models.sale import Sale
from app.dependencies.permissions import require_authenticated_user
from sqlalchemy import func
from app.schemas.sale import (
    CashierSaleContextResponse,
    PosCatalogListResponse,
    SaleCreate,
    SaleCustomerSearchResponse,
    SaleListResponse,
    SaleResponse,
)
from app.services.sale_service import SaleService
from app.services.sale_exchange_quote_service import eligibility as exchange_eligibility, quote as exchange_quote
from pydantic import BaseModel, Field
from decimal import Decimal
from uuid import UUID
from app.services.sale_exchange_confirm_service import confirm as exchange_confirm, history as exchange_history
router=APIRouter(prefix='/sales',tags=['In-store Sales'])

def _err(e):
    if isinstance(e,PermissionError): raise HTTPException(status_code=403,detail=str(e)) from e
    if isinstance(e,LookupError): raise HTTPException(status_code=404,detail=str(e)) from e
    if isinstance(e,ValueError): raise HTTPException(status_code=400,detail=str(e)) from e
    raise e

@router.post('',response_model=SaleResponse,status_code=status.HTTP_201_CREATED)
def create_sale(data:SaleCreate,db:Session=Depends(get_db),current_user:User=Depends(require_sales_create)):
    try:return SaleService.create_sale(db=db,current_user=current_user,data=data)
    except Exception as e:_err(e)

class OfflineCashSaleRequest(SaleCreate):
    amount_received: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    client_operation_id: UUID
    branch_id: int = Field(gt=0)


@router.post('/offline-cash', status_code=status.HTTP_201_CREATED)
def create_offline_cash_sale(
    data: OfflineCashSaleRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_create),
):
    """Confirma venta y efectivo en una sola transacción; UUID asegura reintentos."""
    from sqlalchemy.exc import IntegrityError
    from app.models.payment import Payment
    from app.schemas.cash_payment import CashDeskPaymentCreate
    from app.services.cash_payment_service import CashPaymentService

    def existing_paid():
        sale = db.query(Sale).filter(Sale.client_operation_id == str(data.client_operation_id)).first()
        if sale is None:
            return None
        if (sale.tenant_id != current_user.tenant_id or sale.cashier_id != current_user.id
                or sale.branch_id != data.branch_id or sale.customer_id != data.customer_id):
            raise PermissionError('El UUID pertenece a otra caja u otro usuario.')
        expected = sorted((i.product_variant_id, i.quantity) for i in data.items)
        actual = sorted((i.product_variant_id, i.quantity) for i in sale.items)
        if expected != actual:
            raise ValueError('UUID reutilizado con artículos distintos.')
        if sale.status != 'PAID':
            raise ValueError('Existe una venta pendiente con este UUID; requiere conciliación manual.')
        payment = db.query(Payment).filter(Payment.sale_id == sale.id,
                                           Payment.status == 'APPROVED',
                                           Payment.payment_method == 'CASH').first()
        if not payment:
            raise ValueError('La venta no tiene un pago efectivo confirmado.')
        if Decimal(data.amount_received).quantize(Decimal('0.01')) < Decimal(sale.total_amount):
            raise ValueError('El efectivo indicado no cubre el total de la venta.')
        return {'sale_id': sale.id, 'payment_status': 'APPROVED'}

    try:
        previous = existing_paid()
        if previous is not None:
            return previous
        sale_data = SaleCreate(**data.model_dump(exclude={'amount_received'}))
        sale = SaleService.create_sale(db=db, current_user=current_user, data=sale_data, commit=False)
        result = CashPaymentService.process(
            db=db, current_user=current_user, sale_id=sale['id'],
            data=CashDeskPaymentCreate(payment_method='CASH', amount_received=data.amount_received),
            commit=False,
        )
        db.commit()
        return {'sale_id': sale['id'], 'payment_status': result['status']}
    except IntegrityError:
        db.rollback()
        try:
            previous = existing_paid()
            if previous is not None:
                return previous
        except Exception as e:
            _err(e)
        raise HTTPException(status_code=409, detail='Conflicto de sincronización: vuelve a consultar este UUID.')
    except Exception as e:
        db.rollback()
        _err(e)


@router.get('',response_model=SaleListResponse)
def list_sales(
    page:int=Query(1,ge=1),
    page_size:int=Query(10,ge=1,le=100),
    search:str|None=Query(None,max_length=100),
    branch_id:int|None=Query(None,ge=1),
    cashier_id:int|None=Query(None,ge=1),
    customer_id:int|None=Query(None,ge=1),
    customer_search:str|None=Query(None,max_length=100),
    cashier_search:str|None=Query(None,max_length=100),
    payment_method:Literal['CASH','CARD','QR','TRANSFER']|None=Query(None),
    sale_status:Literal['PENDING','PAID','CANCELLED','REFUNDED']|None=Query(None,alias='status'),
    date_from:datetime|None=None,
    date_to:datetime|None=None,
    db:Session=Depends(get_db),
    current_user:User=Depends(require_sales_view),
):
    if date_from and date_to and date_from>date_to:
        raise HTTPException(400,'date_from no puede ser posterior a date_to.')
    try:
        return SaleService.list_sales(
            db=db,
            current_user=current_user,
            page=page,
            page_size=page_size,
            search=search,
            branch_id=branch_id,
            cashier_id=cashier_id,
            customer_id=customer_id,
            customer_search=customer_search,
            cashier_search=cashier_search,
            payment_method=payment_method,
            sale_status=sale_status,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as e:
        _err(e)


# Historial POS personal: no concede permisos administrativos ni expone ventas ajenas.
# Debe ir antes de /{sale_id} para no colisionar con rutas dinámicas.
@router.get('/mine', response_model=SaleListResponse)
def list_my_pos_sales(
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    payment_method: Literal['CASH', 'CARD', 'QR', 'TRANSFER'] | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    from app.models.payment import Payment
    if not current_user.role or current_user.role.name != 'CLIENTE':
        raise HTTPException(status_code=403, detail='Solo clientes pueden consultar sus compras presenciales.')
    query = db.query(Sale).filter(Sale.customer_id == current_user.id)
    if payment_method:
        query = query.filter(Sale.payments.any(
            (Payment.payment_method == payment_method) & (Payment.status == 'APPROVED')
        ))
    total = query.count()
    rows = query.order_by(Sale.created_at.desc(), Sale.id.desc()).offset((page - 1) * page_size).limit(page_size).all()
    items = [SaleService._serialize(SaleService._get(db, row.id)) for row in rows]
    return {'items': items, 'page': page, 'page_size': page_size,
            'total': total, 'total_pages': (total + page_size - 1) // page_size}


@router.get('/mine/{sale_id}', response_model=SaleResponse)
def my_pos_sale_detail(
    sale_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_authenticated_user),
):
    if not current_user.role or current_user.role.name != 'CLIENTE':
        raise HTTPException(status_code=403, detail='Solo clientes pueden consultar sus compras presenciales.')
    sale = db.query(Sale).filter(Sale.id == sale_id, Sale.customer_id == current_user.id).first()
    if sale is None:
        raise HTTPException(status_code=404, detail='Venta no encontrada.')
    return SaleService._serialize(SaleService._get(db, sale.id))


@router.get('/context',response_model=CashierSaleContextResponse)
def get_cashier_context(db:Session=Depends(get_db),current_user:User=Depends(require_sales_create)):
    try:return SaleService.get_cashier_context(db=db,current_user=current_user)
    except Exception as e:_err(e)

@router.get('/catalog',response_model=PosCatalogListResponse)
def get_pos_catalog(page:int=Query(1,ge=1),page_size:int=Query(24,ge=1,le=100),search:str|None=Query(None,max_length=100),db:Session=Depends(get_db),current_user:User=Depends(require_sales_create)):
    try:return SaleService.get_pos_catalog(db=db,current_user=current_user,page=page,page_size=page_size,search=search)
    except Exception as e:_err(e)

@router.get('/customers',response_model=SaleCustomerSearchResponse)
def search_sale_customers(page:int=Query(1,ge=1),page_size:int=Query(10,ge=1,le=50),search:str|None=Query(None,max_length=100),db:Session=Depends(get_db),current_user:User=Depends(require_sales_create)):
    try:return SaleService.search_customers(db=db,current_user=current_user,page=page,page_size=page_size,search=search)
    except Exception as e:_err(e)

class ExchangeQuoteRequest(BaseModel):
    sale_item_id: int = Field(gt=0)
    replacement_variant_id: int = Field(gt=0)
    quantity: int = Field(gt=0)


@router.get('/{sale_id}/exchange-eligibility')
def get_exchange_eligibility(
    sale_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_view),
):
    try:
        return exchange_eligibility(db, current_user, sale_id)
    except Exception as e:
        _err(e)


@router.post('/{sale_id}/exchange-quote')
def get_exchange_quote(
    data: ExchangeQuoteRequest,
    sale_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_sales_view),
):
    try:
        return exchange_quote(db, current_user, sale_id, data.sale_item_id,
                              data.replacement_variant_id, data.quantity)
    except Exception as e:
        _err(e)


class ExchangeConfirmRequest(ExchangeQuoteRequest):
    client_operation_id: str = Field(min_length=36,max_length=36)
    item_condition: Literal['RESELLABLE']
    amount_received: Decimal = Field(ge=0, decimal_places=2)
    expected_additional: Decimal = Field(ge=0, decimal_places=2)

@router.get('/{sale_id}/exchanges')
def list_sale_exchanges(sale_id:int=Path(...,ge=1),db:Session=Depends(get_db),current_user:User=Depends(require_sales_view)):
    try:return exchange_history(db,current_user,sale_id)
    except Exception as e:_err(e)

@router.post('/{sale_id}/exchange-confirm',status_code=status.HTTP_201_CREATED)
def confirm_sale_exchange(data:ExchangeConfirmRequest,sale_id:int=Path(...,ge=1),
    db:Session=Depends(get_db),current_user:User=Depends(require_sales_create)):
    try:return exchange_confirm(db,current_user,sale_id,**data.model_dump())
    except Exception as e:_err(e)

@router.get('/{sale_id}',response_model=SaleResponse)
def get_sale(sale_id:int=Path(...,ge=1),db:Session=Depends(get_db),current_user:User=Depends(require_sales_view)):
    try:return SaleService.get_sale(db=db,current_user=current_user,sale_id=sale_id)
    except Exception as e:_err(e)

@router.post('/{sale_id}/cancel',response_model=SaleResponse)
def cancel_sale(sale_id:int=Path(...,ge=1),db:Session=Depends(get_db),current_user:User=Depends(require_sales_cancel)):
    try:return SaleService.cancel_sale(db=db,current_user=current_user,sale_id=sale_id)
    except Exception as e:_err(e)
