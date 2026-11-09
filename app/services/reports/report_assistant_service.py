from __future__ import annotations

import unicodedata
import re
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

    # Canonical API filter values. An LLM response is untrusted input.
    VALID_ENUMS = {
        "payment_method": {"CASH", "CARD", "QR", "TRANSFER"},
        "stock_state": {"IN_STOCK", "LOW_STOCK", "OUT_OF_STOCK"},
        "item_status": {"PENDING", "RESERVED", "RELEASED", "CONSUMED"},
        "order_status": {"PENDING_PAYMENT", "PAYMENT_FAILED", "PAID", "PREPARING", "READY_FOR_PICKUP", "SHIPPED", "DELIVERED", "COMPLETED", "CANCELLED", "REFUNDED"},
        "payment_status": {"PENDING", "PROCESSING", "APPROVED", "REJECTED", "FAILED", "CANCELLED", "REFUNDED"},
        "delivery_type": {"PICKUP", "DELIVERY"},
        "sales_status": {"PENDING", "PAID", "CANCELLED", "REFUNDED"},
        "reservations_status": {"PENDING", "CONFIRMED", "PREPARING", "READY", "ATTENDED", "COMPLETED", "CANCELLED", "EXPIRED"},
    }

    @classmethod
    def _canonical_enum(cls, report_key: str, key: str, value: Any) -> str | None:
        enum_key = f"{report_key}_status" if key == "status" else key
        valid = cls.VALID_ENUMS.get(enum_key)
        if valid is None:
            return None
        cleaned = str(value).strip().upper()
        return cleaned if cleaned in valid else None

    @staticmethod
    def _norm(value: str) -> str:
        value = unicodedata.normalize("NFKD", value or "")
        value = "".join(ch for ch in value if not unicodedata.combining(ch))
        return " ".join(value.casefold().split())

    @classmethod
    def _resolve_entity(cls, db: Session, model: type, labeler, requested: str, *, tenant_id: int) -> tuple[int | None, str | None]:
        stmt = select(model)
        if hasattr(model, "tenant_id"):
            stmt = stmt.where(model.tenant_id == tenant_id)
        rows = db.scalars(stmt).all()
        wanted = cls._norm(requested)
        if not wanted:
            return None, None

        # La transcripción por voz puede separar nombres comerciales:
        # "Fashion Store Cala Cala" y "FashionStore Cala Cala" son equivalentes.
        # Esta tolerancia se restringe a sucursales del tenant ya filtrado;
        # nunca se elige una coincidencia cuando hay más de una.
        if model is Branch:
            compact = lambda text: re.sub(r"[^a-z0-9]", "", cls._norm(text))
            target = compact(requested)
            matches = [row for row in rows if compact(labeler(row)) == target]
            if len(matches) == 1:
                return matches[0].id, labeler(matches[0])
            if len(matches) > 1:
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
    def _unsafe_command(cls, command: str) -> bool:
        """Read-only report assistant: never reinterpret a mutation as a report."""
        normalized = cls._norm(command)
        # Apply only to imperative requests, not reports ABOUT deleted/cancelled data.
        return bool(re.search(
            r"\b(?:elimina|eliminar|borra|borrar|suprime|suprimir|actualiza|actualizar|"
            r"modifica|modificar|edita|editar|cambia|cambiar|crea|crear|registra|registrar|"
            r"anula|anular|cancela|cancelar)\b\s+"
            r"(?:todas?\s+|todos?\s+|las?\s+|los?\s+|una?\s+|un\s+|"
            r"mis\s+|el\s+|la\s+)*"
            r"(?:ventas?|compras?|pedidos?|reservas?|pagos?|productos?|inventario|"
            r"sucursales?|usuarios?|clientes?|precios?|stock)\b",
            normalized,
        ))

    @classmethod
    def interpret(cls, db: Session, request: ReportAssistantRequest, *, tenant_id: int) -> ReportAssistantResponse:
        if cls._unsafe_command(request.command):
            return ReportAssistantResponse(
                report_key=request.current_report or "sales",
                action="APPLY_FILTERS",
                mode="current",
                filters={},
                can_execute=False,
                message="Este asistente solo consulta y exporta reportes; no puede modificar ni eliminar información.",
                unresolved=["operación no permitida"],
            )
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
            entity_id, label = cls._resolve_entity(db, model, labeler, str(requested), tenant_id=tenant_id)
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
                # An LLM may fill unspecified numeric fields with 0 even when the
                # user never requested a threshold. Do not silently remove sales.
                if key in {"min_total", "max_total", "min_stock", "max_stock"} and str(value).strip() in {"0", "0.0", "0.00"}:
                    import re
                    command = request.command.casefold()
                    names = {"min_total": r"(?:monto|total|precio)\s+m[ií]nimo", "max_total": r"(?:monto|total|precio)\s+m[aá]ximo", "min_stock": r"stock\s+m[ií]nimo", "max_stock": r"stock\s+m[aá]ximo"}
                    if not re.search(names[key] + r"\s*(?::|de|es|igual a)?\s*(?:bs\.?\s*)?0(?:[.,]0+)?\b", command):
                        continue
                enum_key = f"{report_key}_status" if key == "status" else key
                if enum_key in cls.VALID_ENUMS:
                    canonical = cls._canonical_enum(report_key, key, value)
                    if canonical is None:
                        # Report descriptions like "compras digitales" must not
                        # become invented order states such as DIGITAL.
                        continue
                    value = canonical
                if key == "search":
                    normalized_search = cls._norm(str(value))
                    normalized_command = cls._norm(request.command)
                    if report_key == "orders-payments" and normalized_search in {"digital", "digitales", "electronico", "electronicos", "pagos", "compras"} and normalized_search in normalized_command:
                        continue
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

        analysis_kind = parsed.get("analysis_kind")
        if analysis_kind not in {"top_products", "branch_comparison", "weekly_sales", "category_revenue"} or report_key != "sales":
            analysis_kind = None
        if report_key == "sales" and action in {"APPLY_FILTERS", "EXPORT"} and analysis_kind is None:
            command = cls._norm(request.command)
            if ("producto" in command and ("mas vendido" in command or "ranking" in command or "top " in command)):
                analysis_kind = "top_products"
            elif "categor" in command and ("ingreso" in command or "recaud" in command or "mas vendid" in command):
                analysis_kind = "category_revenue"
            elif "seman" in command and ("venta" in command or "grafico" in command):
                analysis_kind = "weekly_sales"
            elif "sucursal" in command and ("compar" in command or "agrup" in command or "por sucursal" in command):
                analysis_kind = "branch_comparison"

        return ReportAssistantResponse(
            analysis_kind=analysis_kind,
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
