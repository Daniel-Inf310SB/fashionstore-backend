from fastapi import APIRouter,Depends,HTTPException,Path,status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.receipts import require_receipt_create
from app.dependencies.sales import require_sales_view
from app.models.user import User
from app.schemas.receipt import ReceiptResponse
from app.services.receipt_service import ReceiptService
router=APIRouter(prefix='/receipts',tags=['Receipts'])

def _err(e):
    if isinstance(e,PermissionError): raise HTTPException(403,str(e)) from e
    if isinstance(e,LookupError): raise HTTPException(404,str(e)) from e
    if isinstance(e,ValueError): raise HTTPException(400,str(e)) from e
    raise e

@router.post('/sales/{sale_id}',response_model=ReceiptResponse,status_code=status.HTTP_201_CREATED)
def issue_sale_receipt(sale_id:int=Path(...,ge=1),db:Session=Depends(get_db),current_user:User=Depends(require_receipt_create)):
    try:return ReceiptService.issue_sale_receipt(db=db,current_user=current_user,sale_id=sale_id)
    except Exception as e:_err(e)

@router.get('/sales/{sale_id}',response_model=ReceiptResponse)
def get_sale_receipt(sale_id:int=Path(...,ge=1),db:Session=Depends(get_db),current_user:User=Depends(require_sales_view)):
    try:return ReceiptService.get_by_sale(db=db,current_user=current_user,sale_id=sale_id)
    except Exception as e:_err(e)
