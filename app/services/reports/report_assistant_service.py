from __future__ import annotations

import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audience import Audience
from app.models.branch import Branch
from app.models.category import Category
from app.models.color import Color
from app.models.product import Product
from app.models.size import Size
from app.models.user import User
from app.schemas.report_assistant import ReportAssistantRequest, ReportAssistantResponse
from app.services.ai.openai_service import OpenAIService
from app.services.reports.report_assistant_prompt import ReportAssistantPrompt


class ReportAssistantService:
    ENTITY_FIELDS = {
        "branch_name": ("branch_id", Branch, lambda x: x.name),
        "customer_name": ("customer_id", User, lambda x: f"{x.first_name} {x.last_name or ''}".strip()),
        "cashier_name": ("cashier_id", User, lambda x: f"{x.first_name} {x.last_name or ''}".strip()),
        "product_name": ("product_id", Product, lambda x: x.name),
        "category_name": ("category_id", Category, lambda x: x.name),
        "audience_name": ("audience_id", Audience, lambda x: x.name),
        "size_name": ("size_id", Size, lambda x: x.name),
        "color_name": ("color_id", Color, lambda x: x.name),
    }

    ALLOWED_BY_REPORT = {
        "sales": {
            "date_from", "date_to", "branch_id", "customer_id", "cashier_id", "product_id",
            "category_id", "audience_id", "payment_method", "status", "min_total", "max_total", "search",
        },
        "inventory": {
            "branch_id", "product_id", "category_id", "audience_id", "size_id", "color_id", "stock_state",
            "is_active", "min_stock", "max_stock", "search",
        },
        "reservations": {
            "date_from", "date_to", "branch_id", "customer_id", "product_id", "category_id", "audience_id",
            "status", "item_status", "search",
        },
        "orders-payments": {
            "date_from", "date_to", "branch_id", "customer_id", "product_id", "category_id", "audience_id",
            "order_status", "payment_status", "payment_method", "delivery_type", "min_total", "max_total", "search",
        },
    }

    @staticmethod
    def _norm(value: str) -> str:
        value = unicodedata.normalize("NFKD", value or "")
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return " ".join(value.casefold().split())

    @classmethod
    def _resolve_entity(cls, db: Session, model: type, labeler, requested: str) -> tuple[int | None, str | None]:
        rows = db.scalars(select(model)).all()
        wanted = cls._norm(requested)
        if not wanted:
            return None, None

        exact = [row for row in rows if cls._norm(labeler(row)) == wanted]
        if len(exact) == 1:
            return exact[0].id, labeler(exact[0])

        contains = [row for row in rows if wanted in cls._norm(labeler(row)) or cls._norm(labeler(row)) in wanted]
        if len(contains) == 1:
            return contains[0].id, labeler(contains[0])

        starts = [row for row in rows if cls._norm(labeler(row)).startswith(wanted)]
        if len(starts) == 1:
            return starts[0].id, labeler(starts[0])

        return None, None

    @classmethod
    def interpret(cls, db: Session, request: ReportAssistantRequest) -> ReportAssistantResponse:
        parsed, usage = OpenAIService.generate_json(
            instructions=ReportAssistantPrompt.build(request.current_report),
            input_data={"command": request.command, "current_report": request.current_report},
        )

        report_key = parsed.get("report_key") or request.current_report or "sales"
        if report_key not in cls.ALLOWED_BY_REPORT:
            report_key = request.current_report or "sales"

        action = parsed.get("action") or "APPLY_FILTERS"
        if action not in {"APPLY_FILTERS", "EXPORT", "CLEAR_FILTERS", "SWITCH_REPORT"}:
            action = "APPLY_FILTERS"

        mode = parsed.get("mode") or "replace"
        if mode not in {"replace", "merge", "current"}:
            mode = "replace"

        export_format = parsed.get("export_format")
        if export_format == "excel":
            export_format = "xlsx"
        elif export_format == "word":
            export_format = "docx"
        if export_format not in {None, "pdf", "xlsx", "docx"}:
            export_format = None

        semantic = parsed.get("filters") if isinstance(parsed.get("filters"), dict) else {}
        resolved: dict[str, Any] = {}
        unresolved: list[str] = []

        for semantic_key, (id_key, model, labeler) in cls.ENTITY_FIELDS.items():
            requested = semantic.get(semantic_key)
            if requested is None or str(requested).strip() == "":
                continue
            entity_id, label = cls._resolve_entity(db, model, labeler, str(requested))
            if entity_id is None:
                unresolved.append(f"{semantic_key}: {requested}")
            else:
                resolved[id_key] = entity_id

        # Non-entity filters are already canonical values from the model.
        passthrough = {
            "date_from", "date_to", "payment_method", "status", "stock_state", "is_active",
            "min_stock", "max_stock", "item_status", "order_status", "payment_status",
            "delivery_type", "min_total", "max_total", "search",
        }
        for key in passthrough:
            value = semantic.get(key)
            if value is not None and value != "":
                resolved[key] = value

        allowed = cls.ALLOWED_BY_REPORT[report_key]
        resolved = {key: value for key, value in resolved.items() if key in allowed}

        can_execute = not unresolved
        message = str(parsed.get("message") or "Comando interpretado.").strip()
        if unresolved:
            message = "No pude identificar con precisión: " + ", ".join(unresolved) + "."

        if action == "EXPORT" and export_format is None:
            can_execute = False
            unresolved.append("formato de exportación")
            message = "Indica si deseas descargar en PDF, Excel o Word."

        return ReportAssistantResponse(
            report_key=report_key,
            action=action,
            mode=mode,
            export_format=export_format,
            filters=resolved,
            can_execute=can_execute,
            message=message,
            unresolved=unresolved,
            usage=usage,
        )
