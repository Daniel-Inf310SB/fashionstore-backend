from __future__ import annotations

from datetime import date, datetime, time, timezone
from decimal import Decimal
from typing import Any


def start_of_day(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.min, tzinfo=timezone.utc)


def end_of_day(value: date | None) -> datetime | None:
    if value is None:
        return None
    return datetime.combine(value, time.max, tzinfo=timezone.utc)


def full_name(user: Any | None) -> str:
    if user is None:
        return "—"
    parts = [getattr(user, "first_name", None), getattr(user, "last_name", None)]
    value = " ".join(str(part).strip() for part in parts if part and str(part).strip())
    return value or getattr(user, "email", None) or "—"


def money(value: Any) -> float:
    if value is None:
        return 0.0
    return float(Decimal(str(value)))


def iso_datetime(value: datetime | None) -> str | None:
    return value.isoformat() if value else None


def clean_filters(filters: Any) -> dict[str, Any]:
    raw = filters.model_dump(exclude_none=True)
    result: dict[str, Any] = {}
    for key, value in raw.items():
        if isinstance(value, (date, datetime)):
            result[key] = value.isoformat()
        elif isinstance(value, Decimal):
            result[key] = float(value)
        else:
            result[key] = value
    return result


def report_payload(*, report_key: str, title: str, filters: Any, summary: dict[str, Any], columns: list[dict[str, str]], rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "report_key": report_key,
        "title": title,
        "generated_at": datetime.now(timezone.utc),
        "filters": clean_filters(filters),
        "summary": summary,
        "columns": columns,
        "rows": rows,
        "total_rows": len(rows),
    }
