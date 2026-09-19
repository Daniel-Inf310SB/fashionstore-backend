from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.ai import (
    require_ai_assistant,
    require_ai_recommendations,
    require_ai_reports,
    require_virtual_fitting,
)
from app.models.user import User
from app.schemas.ai import (
    AIAssistantRequest,
    AIAssistantResponse,
    AIRecommendationRequest,
    AIRecommendationResponse,
    AIReportRequest,
    AIReportResponse,
    AIVirtualTryOnResponse,
)
from app.services.ai.ai_service import AIService
from app.services.ai.virtual_try_on_service import VirtualTryOnService


router = APIRouter(prefix="/ai", tags=["Artificial Intelligence"])


@router.post("/recommendations", response_model=AIRecommendationResponse)
def get_recommendations(
    data: AIRecommendationRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_ai_recommendations),
):
    try:
        return AIService.recommendations(db, data)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.post("/assistant", response_model=AIAssistantResponse)
def ask_assistant(
    data: AIAssistantRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_ai_assistant),
):
    try:
        return AIService.assistant(db, data)
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.post("/reports", response_model=AIReportResponse)
def generate_intelligent_report(
    data: AIReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_ai_reports),
):
    try:
        return AIService.intelligent_report(db, current_user, data)
    except LookupError as error:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(error)) from error
    except PermissionError as error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(error)) from error
    except RuntimeError as error:
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=str(error)) from error


@router.post("/virtual-try-on", response_model=AIVirtualTryOnResponse)
async def generate_virtual_try_on(
    variant_id: int = Form(..., ge=1),
    person_image: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_virtual_fitting),
):
    try:
        content = await person_image.read()
        return VirtualTryOnService.generate(
            db,
            variant_id=variant_id,
            person_image=content,
            person_content_type=person_image.content_type,
            user_id=current_user.id,
        )
    except LookupError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(error),
        ) from error
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        ) from error
