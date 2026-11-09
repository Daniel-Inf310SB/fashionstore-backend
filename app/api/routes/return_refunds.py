from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.permissions import require_authenticated_user
from app.models.user import User
from app.schemas.return_refund import RefundOut, RefundPreview
from app.services.return_refund_service import ReturnRefundService as S

router=APIRouter(prefix='/return-refunds',tags=['Return Refunds - Test Only'])
def call(fn,*args):
    try:return fn(*args)
    except PermissionError as ex:raise HTTPException(403,str(ex)) from ex
    except LookupError as ex:raise HTTPException(404,str(ex)) from ex
    except ValueError as ex:raise HTTPException(409,str(ex)) from ex

@router.get('/{return_id}/preview',response_model=RefundPreview)
def preview(return_id:int,db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return call(S.preview,db,user,return_id)

@router.post('/{return_id}/prepare',response_model=RefundOut)
def prepare(return_id:int,db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return call(S.prepare,db,user,return_id)

@router.post('/{return_id}/execute-test',response_model=RefundOut)
def execute_test(return_id:int,db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return call(S.execute,db,user,return_id)

@router.get('/{return_id}',response_model=RefundOut)
def status(return_id:int,db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return call(S.status,db,user,return_id)

@router.post('/{return_id}/reconcile-test',response_model=RefundOut)
def reconcile(return_id:int,db:Session=Depends(get_db),user:User=Depends(require_authenticated_user)):
    return call(S.reconcile,db,user,return_id)
