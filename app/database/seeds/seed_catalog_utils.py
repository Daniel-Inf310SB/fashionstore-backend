from __future__ import annotations

from datetime import date, datetime, timedelta
from decimal import Decimal
from typing import Any, Iterable

from sqlalchemy import inspect, or_, select
from sqlalchemy.orm import Session


def model_columns(model) -> dict[str, Any]:
    """Devuelve las columnas SQLAlchemy reales del modelo."""
    mapper = inspect(model)
    return {column.key: column for column in mapper.columns}


def existing_payload(model, payload: dict[str, Any]) -> dict[str, Any]:
    """
    Conserva solo las claves que realmente existen como columnas
    en el modelo actual. Así los seeds toleran pequeños cambios
    de nombres/campos sin romper por argumentos desconocidos.
    """
    columns = model_columns(model)
    return {
        key: value
        for key, value in payload.items()
        if key in columns
    }


def first_existing_field(model, *candidates: str) -> str | None:
    columns = model_columns(model)
    for candidate in candidates:
        if candidate in columns:
            return candidate
    return None


def get_required_missing_columns(
    model,
    payload: dict[str, Any],
) -> list[str]:
    """
    Detecta columnas obligatorias sin default que el payload no llena.
    Excluye PK autoincremental y FKs que normalmente cargamos aparte.
    """
    columns = model_columns(model)
    missing: list[str] = []

    for key, column in columns.items():
        if key in payload:
            continue

        if column.primary_key and getattr(column, "autoincrement", False):
            continue

        if column.nullable:
            continue

        if column.default is not None or column.server_default is not None:
            continue

        if column.foreign_keys:
            continue

        if key in {"created_at", "updated_at"}:
            continue

        missing.append(key)

    return missing


def seed_lookup_field(
    model,
    preferred: Iterable[str] = (
        "sku",
        "code",
        "slug",
        "name",
        "title",
    ),
) -> str:
    field = first_existing_field(model, *preferred)

    if field is None:
        raise RuntimeError(
            f"No se encontró un campo estable para hacer upsert en "
            f"{model.__name__}. Esperados: {', '.join(preferred)}"
        )

    return field


def find_one_by(
    db: Session,
    model,
    field: str,
    value: Any,
):
    return db.scalar(
        select(model).where(
            getattr(model, field) == value
        )
    )


def upsert_model(
    db: Session,
    model,
    payload: dict[str, Any],
    *,
    lookup_field: str | None = None,
):
    """
    UPSERT idempotente por un campo estable.
    Actualiza si existe; crea si no existe.
    """
    payload = existing_payload(model, payload)

    if lookup_field is None:
        lookup_field = seed_lookup_field(model)

    if lookup_field not in payload:
        raise RuntimeError(
            f"El payload de {model.__name__} no contiene "
            f"el campo de búsqueda '{lookup_field}'."
        )

    obj = find_one_by(
        db,
        model,
        lookup_field,
        payload[lookup_field],
    )

    if obj is None:
        missing = get_required_missing_columns(
            model,
            payload,
        )

        if missing:
            raise RuntimeError(
                f"Faltan campos obligatorios para crear "
                f"{model.__name__}: {', '.join(missing)}"
            )

        obj = model(**payload)
        db.add(obj)
    else:
        for key, value in payload.items():
            setattr(obj, key, value)

    db.flush()
    return obj


def safe_bool_payload(
    model,
    *,
    active: bool = True,
) -> dict[str, Any]:
    columns = model_columns(model)
    payload: dict[str, Any] = {}

    for field in (
        "is_active",
        "active",
        "enabled",
    ):
        if field in columns:
            payload[field] = active
            break

    return payload


def resolve_id(obj) -> int:
    value = getattr(obj, "id", None)
    if value is None:
        raise RuntimeError(
            f"{obj.__class__.__name__} no tiene id luego de flush()."
        )
    return value


def relation_exists(
    db: Session,
    model,
    **filters,
) -> bool:
    conditions = [
        getattr(model, key) == value
        for key, value in filters.items()
    ]

    return (
        db.scalar(
            select(model).where(*conditions)
        )
        is not None
    )


def add_relation_if_missing(
    db: Session,
    model,
    payload: dict[str, Any],
    *,
    unique_by: tuple[str, ...],
):
    payload = existing_payload(model, payload)

    filters = {
        key: payload[key]
        for key in unique_by
        if key in payload
    }

    if len(filters) != len(unique_by):
        raise RuntimeError(
            f"No se pueden validar relaciones de "
            f"{model.__name__}; faltan claves: {unique_by}"
        )

    if relation_exists(
        db,
        model,
        **filters,
    ):
        return db.scalar(
            select(model).where(
                *[
                    getattr(model, key) == value
                    for key, value in filters.items()
                ]
            )
        )

    obj = model(**payload)
    db.add(obj)
    db.flush()
    return obj
