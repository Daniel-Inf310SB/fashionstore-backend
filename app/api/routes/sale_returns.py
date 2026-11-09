"""Devoluciones presenciales; no utiliza endpoints de Stripe ni de pedidos online."""
from fastapi import APIRouter, Depends, HTTPException, Path
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.permissions import require_authenticated_user
from app.models.user import User
from app.schemas.sale_return import SaleReturnCreate, SaleReturnDecision, SaleReturnInspection, SaleReturnRefund
from app.services.sale_return_service import SaleReturnService as Service

router=APIRouter(prefix='/sale-returns',tags=['In-store Returns'])

def _run(fn,*args):
    try:return fn(*args)
    except PermissionError as e:raise HTTPException(403,str(e)) from e
    except LookupError as e:raise HTTPException(404,str(e)) from e
    except ValueError as e:raise HTTPException(409,str(e)) from e

@router.get('/eligibility/{sale_id}')
def eligibility(sale_id:int=Path(ge=1),db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return _run(Service.eligibility,db,user,sale_id)

@router.post('',status_code=201)
def request_return(data:SaleReturnCreate,db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return _run(Service.create,db,user,data)

@router.get('')
def list_returns(db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return _run(Service.list,db,user)

@router.get('/{return_id}')
def detail(return_id:int=Path(ge=1),db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return _run(Service.detail,db,user,return_id)

@router.post('/{return_id}/decision')
def decision(data:SaleReturnDecision,return_id:int=Path(ge=1),db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return _run(Service.decide,db,user,return_id,data)

@router.post('/{return_id}/receive')
def receive(return_id:int=Path(ge=1),db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return _run(Service.receive,db,user,return_id)

@router.post('/{return_id}/inspect')
def inspect(data:SaleReturnInspection,return_id:int=Path(ge=1),db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return _run(Service.inspect,db,user,return_id,data)

@router.post('/{return_id}/refund-confirmation')
def refund(data:SaleReturnRefund,return_id:int=Path(ge=1),db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return _run(Service.refund,db,user,return_id,data)
