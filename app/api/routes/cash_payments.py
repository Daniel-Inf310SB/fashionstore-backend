from fastapi import APIRouter,Depends,HTTPException,Path,status
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.cash_payments import require_cash_payment_process
from app.models.user import User
from app.schemas.cash_payment import CashDeskPaymentCreate,CashDeskPaymentResponse,ReservationCheckoutCreate,ReservationCheckoutResponse
from app.services.reservation_checkout_service import ReservationCheckoutService
from app.services.cash_payment_service import CashPaymentService
router=APIRouter(prefix='/cash-payments',tags=['Cash Desk Payments'])

@router.post('/sales/{sale_id}',response_model=CashDeskPaymentResponse,status_code=status.HTTP_201_CREATED)
def process_sale_payment(data:CashDeskPaymentCreate,sale_id:int=Path(...,ge=1),db:Session=Depends(get_db),current_user:User=Depends(require_cash_payment_process)):
    try:return CashPaymentService.process(db=db,current_user=current_user,sale_id=sale_id,data=data)
    except PermissionError as e: raise HTTPException(403,str(e)) from e
    except LookupError as e: raise HTTPException(404,str(e)) from e
    except ValueError as e: raise HTTPException(400,str(e)) from e


@router.post('/reservations/{reservation_id}', response_model=ReservationCheckoutResponse,
             status_code=status.HTTP_201_CREATED)
def checkout_reservation(data: ReservationCheckoutCreate,
                         reservation_id: int=Path(..., ge=1),
                         db: Session=Depends(get_db),
                         current_user: User=Depends(require_cash_payment_process)):
    try:
        return ReservationCheckoutService.process(db=db, reservation_id=reservation_id,
                                                 current_user=current_user, data=data)
    except PermissionError as e: raise HTTPException(403, str(e)) from e
    except LookupError as e: raise HTTPException(404, str(e)) from e
    except ValueError as e: raise HTTPException(400, str(e)) from e

@router.get('/reservations/lookup/{reservation_code}')
def lookup_reservation_for_cashier(reservation_code: str,
                                   db: Session=Depends(get_db),
                                   current_user: User=Depends(require_cash_payment_process)):
    from decimal import Decimal
    from app.models.reservation import Reservation
    from app.models.reservation_item import ReservationItem
    from app.models.employee_branch import EmployeeBranch
    if current_user.role is None or current_user.role.name != 'CAJERO':
        raise HTTPException(403, 'Solo un cajero puede consultar reservas para cobro.')
    reservation = db.query(Reservation).filter(
        Reservation.reservation_code == reservation_code.strip().upper(),
        Reservation.tenant_id == current_user.tenant_id).first()
    if reservation is None:
        raise HTTPException(404, 'No existe esta reserva en tu empresa.')
    allowed = db.query(EmployeeBranch.id).filter(
        EmployeeBranch.user_id == current_user.id,
        EmployeeBranch.branch_id == reservation.branch_id,
        EmployeeBranch.is_active.is_(True)).first()
    if not allowed:
        raise HTTPException(403, 'La reserva pertenece a otra sucursal.')
    if reservation.status != 'ATTENDED':
        raise HTTPException(400, f'La reserva está {reservation.status}; debe estar ATENDIDA.')
    items = db.query(ReservationItem).filter(ReservationItem.reservation_id == reservation.id).all()
    if not items or any(i.status != 'RESERVED' for i in items):
        raise HTTPException(400, 'La reserva no tiene todas sus prendas reservadas.')
    return {'id': reservation.id, 'code': reservation.reservation_code,
            'customer_id': reservation.customer_id, 'branch_id': reservation.branch_id,
            'status': reservation.status,
            'units': sum(item.quantity for item in items),
            'amount': str(sum((Decimal(item.unit_price) * item.quantity for item in items), Decimal(0)))}
