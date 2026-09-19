from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.customer_assistant import require_customer_assistant
from app.models.user import User
from app.schemas.customer_assistant import (
    CustomerAssistantExecuteRequest,
    CustomerAssistantExecuteResponse,
    CustomerAssistantInterpretRequest,
    CustomerAssistantInterpretResponse,
)
from app.services.customer_assistant import CustomerAssistantService


router = APIRouter(
    prefix="/customer-assistant",
    tags=["Customer AI Assistant"],
)


def _handle(error: Exception) -> None:
    if isinstance(error, PermissionError):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    if isinstance(error, LookupError):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    if isinstance(error, ValueError):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error)) from error
    if isinstance(error, RuntimeError):
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error
    raise error


@router.post("/interpret", response_model=CustomerAssistantInterpretResponse)
def interpret_customer_command(
    data: CustomerAssistantInterpretRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer_assistant),
):
    try:
        result, usage = CustomerAssistantService.interpret(
            db=db,
            user=current_user,
            command=data.command,
            context=data.context,
        )
        return {
            "command": data.command,
            "result": result,
            "usage": usage,
        }
    except Exception as error:
        _handle(error)


@router.post("/execute", response_model=CustomerAssistantExecuteResponse)
def execute_customer_command(
    data: CustomerAssistantExecuteRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_customer_assistant),
):
    try:
        executed = CustomerAssistantService.execute(
            db=db,
            user=current_user,
            data=data,
        )
        return {
            "action": data.action,
            "message": executed["message"],
            "data": executed.get("data"),
            "navigation": executed.get("navigation"),
        }
    except Exception as error:
        _handle(error)
