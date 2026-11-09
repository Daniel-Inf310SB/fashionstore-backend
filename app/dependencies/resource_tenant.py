"""Fail-closed tenancy checks for legacy endpoints using global services."""
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.product import Product
from app.models.branch import Branch


def require_owned_record(db: Session, actor: User, model: type, record_id: int) -> None:
    if actor.tenant_id is None:
        raise HTTPException(status_code=403, detail="La cuenta no tiene una empresa asignada.")
    item = db.query(model.id).filter(
        model.id == record_id,
        model.tenant_id == actor.tenant_id,
    ).first()
    if item is None:
        raise HTTPException(status_code=404, detail="El registro no existe en tu empresa.")
