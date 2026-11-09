from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.permissions import require_authenticated_user
from app.models.user import User
from app.schemas.post_sale import (
    PostSaleCreate, PostSaleDecision, PostSaleInspection, PostSaleQuote,
    PostSaleSettlementIn,
)
from app.services.post_sale_service import PostSaleService as Service

router = APIRouter(prefix="/post-sale", tags=["Unified Post-sale"])


def _run(fn, *args, **kwargs):
    try:
        return fn(*args, **kwargs)
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/eligibility/{source_channel}/{source_id}")
def eligibility(
    source_channel: Literal["ONLINE", "POS"],
    source_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.eligibility, db, user, source_channel, source_id)


@router.post("/cases", status_code=201)
def create_case(
    data: PostSaleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.create, db, user, data, False)


@router.post("/cases/staff-assisted", status_code=201)
def create_staff_assisted_case(
    data: PostSaleCreate,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    """Register a POS return/change for a walk-in customer without a linked account."""
    return _run(Service.create, db, user, data, True)


@router.get("/cases/mine")
def my_cases(
    status: str | None = Query(default=None, max_length=28),
    channel: Literal["ONLINE", "POS"] | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.list, db, user, True, status, channel)


@router.get("/cases")
def list_cases(
    status: str | None = Query(default=None, max_length=28),
    channel: Literal["ONLINE", "POS"] | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.list, db, user, False, status, channel)


@router.get("/cases/{case_id}")
def detail(
    case_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.detail, db, user, case_id)


@router.post("/cases/{case_id}/decision")
def decision(
    data: PostSaleDecision,
    case_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.decide, db, user, case_id, data)


@router.post("/cases/{case_id}/receive")
def receive(
    case_id: int = Path(..., ge=1),
    note: str | None = Query(default=None, max_length=1000),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.receive, db, user, case_id, note)


@router.post("/cases/{case_id}/inspection")
def inspect(
    data: PostSaleInspection,
    case_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.inspect, db, user, case_id, data)


@router.post("/cases/{case_id}/quote")
def quote_exchange(
    data: PostSaleQuote,
    case_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.quote_exchange, db, user, case_id, data)


@router.post("/cases/{case_id}/settlement")
def settle(
    data: PostSaleSettlementIn,
    case_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.settle, db, user, case_id, data)


@router.post("/cases/{case_id}/settlement/reconcile-stripe")
def reconcile_stripe(
    case_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.reconcile_stripe, db, user, case_id)


@router.post("/cases/{case_id}/complete")
def complete(
    case_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.complete, db, user, case_id)


@router.post("/cases/{case_id}/cancel")
def cancel(
    case_id: int = Path(..., ge=1),
    reason: str | None = Query(default=None, max_length=500),
    db: Session = Depends(get_db),
    user: User = Depends(require_authenticated_user),
):
    return _run(Service.cancel, db, user, case_id, reason)
