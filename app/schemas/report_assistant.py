from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.reports import ExportFormat

ReportKey = Literal["sales", "inventory", "reservations", "orders-payments"]
AssistantAction = Literal["APPLY_FILTERS", "EXPORT", "CLEAR_FILTERS", "SWITCH_REPORT"]
AssistantMode = Literal["replace", "merge", "current"]


class ReportAssistantRequest(BaseModel):
    command: str = Field(min_length=2, max_length=500)
    current_report: ReportKey | None = None
    current_filters: dict[str, Any] = Field(default_factory=dict)


class ReportAssistantResponse(BaseModel):
    report_key: ReportKey
    action: AssistantAction
    mode: AssistantMode = "replace"
    export_format: ExportFormat | None = None
    filters: dict[str, Any] = Field(default_factory=dict)
    can_execute: bool = True
    message: str
    unresolved: list[str] = Field(default_factory=list)
    usage: dict[str, int | None] = Field(default_factory=dict)
