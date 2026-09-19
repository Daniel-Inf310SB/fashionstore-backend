from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies.dashboard import get_dashboard_user
from app.models.user import User
from app.schemas.dashboard import DashboardResponse
from app.services.dashboard_service import DashboardService


router = APIRouter(
    prefix="/dashboard",
    tags=["Dashboard"],
)


def _handle_error(exc: Exception):
    if isinstance(exc, PermissionError):
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    raise exc


@router.get("/summary", response_model=DashboardResponse)
def dashboard_summary(
    branch_id: int | None = Query(None, ge=1),
    date_from: date | None = Query(None),
    date_to: date | None = Query(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_dashboard_user),
):
    """
    Dashboard administrativo consolidado.

    - ADMINISTRADOR: branch_id es opcional. Sin branch_id consulta todas las sucursales.
    - ENCARGADO_SUCURSAL: queda limitado a su sucursal activa, incluso si intenta enviar otra.
    - Sin fechas: últimos 30 días incluyendo hoy.
    """
    try:
        return DashboardService.build(
            db,
            current_user=current_user,
            branch_id=branch_id,
            date_from=date_from,
            date_to=date_to,
        )
    except Exception as exc:
        _handle_error(exc)
