from fastapi import APIRouter,Depends,HTTPException,Path,status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.cash_payments import require_cash_payment_process
from app.models.user import User
from app.schemas.cash_payment import CashDeskPaymentCreate,CashDeskPaymentResponse
from app.services.cash_payment_service import CashPaymentService
router=APIRouter(prefix='/cash-payments',tags=['Cash Desk Payments'])

@router.post('/sales/{sale_id}',response_model=CashDeskPaymentResponse,status_code=status.HTTP_201_CREATED)
def process_sale_payment(data:CashDeskPaymentCreate,sale_id:int=Path(...,ge=1),db:Session=Depends(get_db),current_user:User=Depends(require_cash_payment_process)):
    try:return CashPaymentService.process(db=db,current_user=current_user,sale_id=sale_id,data=data)
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except LookupError as e: raise HTTPException(404,str(e)) from e
    except ValueError as e: raise HTTPException(400,str(e)) from e
