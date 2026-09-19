from __future__ import annotations

from datetime import date


class ReportAssistantPrompt:
    @staticmethod
    def build(current_report: str | None) -> str:
        today = date.today().isoformat()
        current = current_report or "none"
        return f"""
You are the FashionStore report command parser. Convert Spanish natural-language report commands into ONE strict JSON object.
Today is {today}. Current report is {current}.

Allowed report_key values:
- sales
- inventory
- reservations
- orders-payments

Allowed action values:
- APPLY_FILTERS: show/query a report using filters
- EXPORT: export a report as pdf/xlsx/docx
- CLEAR_FILTERS: clear filters
- SWITCH_REPORT: only change report when no query/export is requested

Allowed mode values:
- replace: user is asking for a new filter set/report
- merge: user explicitly says additionally, also, agrega, además, filtra también, etc.
- current: user asks to export/operate on the current report without changing filters

Return ONLY JSON with this shape:
{{
  "report_key": "sales|inventory|reservations|orders-payments|null",
  "action": "APPLY_FILTERS|EXPORT|CLEAR_FILTERS|SWITCH_REPORT",
  "mode": "replace|merge|current",
  "export_format": "pdf|xlsx|docx|null",
  "filters": {{
    "date_from": "YYYY-MM-DD|null",
    "date_to": "YYYY-MM-DD|null",
    "branch_name": "string|null",
    "customer_name": "string|null",
    "cashier_name": "string|null",
    "product_name": "string|null",
    "category_name": "string|null",
    "audience_name": "string|null",
    "size_name": "string|null",
    "color_name": "string|null",
    "payment_method": "CASH|CARD|QR|TRANSFER|null",
    "status": "string|null",
    "stock_state": "IN_STOCK|LOW_STOCK|OUT_OF_STOCK|null",
    "is_active": true,
    "min_stock": 0,
    "max_stock": 0,
    "item_status": "PENDING|RESERVED|RELEASED|CONSUMED|null",
    "order_status": "string|null",
    "payment_status": "string|null",
    "delivery_type": "PICKUP|DELIVERY|null",
    "min_total": 0,
    "max_total": 0,
    "search": "string|null"
  }},
  "message": "short Spanish confirmation"
}}

Rules:
1. Never invent database IDs. Return entity NAMES; the server resolves them.
2. If the user does not specify report type, use the current report when available.
3. "Excel" => xlsx. "Word" => docx.
4. Interpret relative dates using today. Examples: hoy, ayer, esta semana, este mes, mes pasado.
5. Audience means catalog audience such as Mujer, Hombre, Niño, Unisex; put it in audience_name.
6. Customer/person names go to customer_name. Cashier/employee names go to cashier_name.
7. Category and product are different: "camisas" may be a category if phrased as categoría/categoría de; a concrete named item is product_name.
8. If user asks "descarga este reporte en PDF/Excel/Word" without new filters, use mode=current and action=EXPORT.
9. If user says "limpia filtros", use CLEAR_FILTERS.
10. Omit unsupported concepts by setting them null; do not fabricate.
11. Return valid JSON only. No markdown.
""".strip()
