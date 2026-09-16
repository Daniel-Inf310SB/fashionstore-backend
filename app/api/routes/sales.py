from datetime import datetime
from typing import Literal
from fastapi import APIRouter,Depends,HTTPException,Path,Query,status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.sales import require_sales_cancel, require_sales_create, require_sales_view
from app.models.user import User
from app.schemas.sale import (
    CashierSaleContextResponse,
    PosCatalogListResponse,
    SaleCreate,
    SaleCustomerSearchResponse,
    SaleListResponse,
    SaleResponse,
)
from app.services.sale_service import SaleService
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

@router.get('/{sale_id}',response_model=SaleResponse)
def get_sale(sale_id:int=Path(...,ge=1),db:Session=Depends(get_db),current_user:User=Depends(require_sales_view)):
    try:return SaleService.get_sale(db=db,current_user=current_user,sale_id=sale_id)
    except Exception as e:_err(e)

@router.post('/{sale_id}/cancel',response_model=SaleResponse)
def cancel_sale(sale_id:int=Path(...,ge=1),db:Session=Depends(get_db),current_user:User=Depends(require_sales_cancel)):
    try:return SaleService.cancel_sale(db=db,current_user=current_user,sale_id=sale_id)
    except Exception as e:_err(e)
