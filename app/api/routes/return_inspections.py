from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.dependencies.permissions import require_authenticated_user
from app.models.user import User
from app.schemas.return_inspection import InspectionDecision, InspectionOut, InspectionLineOut
from app.services.return_inspection_service import ReturnInspectionService

router = APIRouter(prefix='/return-inspections', tags=['Return Inspections - Phase 2B'])


def run(fn, *args):
    try:
        return fn(*args)
    except PermissionError as exc:
        raise HTTPException(403, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(409, detail=str(exc)) from exc


@router.get('/{return_id}/items', response_model=list[InspectionLineOut])
def items(return_id: int, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return run(ReturnInspectionService.list_lines, db, user, return_id)


@router.post('/{return_id}/items/{return_item_id}/inspect', response_model=InspectionOut)
def inspect_item(return_id: int, return_item_id: int, data: InspectionDecision, db: Session = Depends(get_db), user: User = Depends(require_authenticated_user)):
    return run(ReturnInspectionService.decide, db, user, return_id, return_item_id, data)
