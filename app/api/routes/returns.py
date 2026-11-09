from fastapi import APIRouter, Depends, HTTPException, status
from decimal import Decimal
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.permissions import require_authenticated_user
from app.models.user import User
from app.models.return_refund import ReturnRefund
from app.schemas.return_request import ReturnCreate, ReturnDecision, ReturnOut, ReturnEligibilityOut
from app.services.return_service import ReturnService

router = APIRouter(prefix="/returns", tags=["Purchase Returns - Phase 1"])

def execute(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except PermissionError as ex:
        raise HTTPException(status_code=403, detail=str(ex)) from ex
    except LookupError as ex:
        raise HTTPException(status_code=404, detail=str(ex)) from ex
    except ValueError as ex:
        raise HTTPException(status_code=400, detail=str(ex)) from ex

@router.post("", response_model=ReturnOut, status_code=status.HTTP_201_CREATED)
def create(data: ReturnCreate, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return execute(ReturnService.create, db, user, data)

@router.get("/mine", response_model=list[ReturnOut])
def mine(db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return execute(ReturnService.list, db, user, mine=True)

@router.get("", response_model=list[ReturnOut])
def list_all(db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return execute(ReturnService.list, db, user)

@router.get("/orders/{order_id}/eligibility", response_model=ReturnEligibilityOut)
def eligibility(order_id: int, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    """Allowed quantities and variants for the authenticated customer's order."""
    return execute(ReturnService.eligibility, db, user, order_id)

@router.get("/{request_id}", response_model=ReturnOut)
def detail(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return execute(ReturnService.get, db, user, request_id)

@router.post("/{request_id}/approve", response_model=ReturnOut)
def approve(request_id: int, data: ReturnDecision, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return execute(ReturnService.change, db, user, request_id, "approve", data.note)

@router.post("/{request_id}/reject", response_model=ReturnOut)
def reject(request_id: int, data: ReturnDecision, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return execute(ReturnService.change, db, user, request_id, "reject", data.note)

@router.post("/{request_id}/receive", response_model=ReturnOut)
def receive(request_id: int, data: ReturnDecision, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return execute(ReturnService.change, db, user, request_id, "receive", data.note)

@router.post("/{request_id}/cancel", response_model=ReturnOut)
def cancel(request_id: int, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return execute(ReturnService.cancel, db, user, request_id)


class CustomerRefundStatus(BaseModel):
    return_request_id: int
    status: str
    amount: Decimal | None = None
    currency: str | None = None


@router.get("/{request_id}/refund-status", response_model=CustomerRefundStatus)
def refund_status(
    request_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    # Reutilizar la comprobación existente de tenant, propiedad del cliente y rol.
    # ReturnService.get devuelve 404 si otro cliente intenta acceder.
    req = execute(ReturnService.get, db, user, request_id)
    refund = db.scalar(
        select(ReturnRefund).where(
            ReturnRefund.return_request_id == req.id,
            ReturnRefund.tenant_id == req.tenant_id,
        )
    )
    if refund is None:
        return CustomerRefundStatus(return_request_id=req.id, status="NOT_STARTED")
    # Nunca revelar payment_id, idempotency_key, failure_reason ni credenciales.
    return CustomerRefundStatus(
        return_request_id=req.id,
        status=refund.status,
        amount=refund.amount,
        currency=refund.currency,
    )
