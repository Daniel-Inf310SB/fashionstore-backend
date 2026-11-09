from unittest.mock import patch
from app.services.reports.report_assistant_service import ReportAssistantService
from app.services.reports.report_assistant_prompt import ReportAssistantPrompt
from app.services.reports.export_service import ReportExportService


def test_prompt_uses_null_for_unrequested_numeric_limits():
    prompt = ReportAssistantPrompt.build("sales")
    assert '"max_total": null' in prompt
    assert '"min_total": null' in prompt


def test_ai_ignores_unspecified_zero_ceiling():
    from app.schemas.report_assistant import ReportAssistantRequest
    request = ReportAssistantRequest(command="Muéstrame ventas de octubre", current_report="sales")
    payload = {"report_key": "sales", "filters": {"date_from":"2026-10-01", "date_to":"2026-10-31", "max_total":0, "min_total":0}, "action":"APPLY_FILTERS"}
    with patch("app.services.reports.report_assistant_service.OpenAIService.generate_json", return_value=(payload, {})):
        result = ReportAssistantService.interpret(None, request, tenant_id=1)
    filters = result.filters
    assert filters.get("max_total") is None
    assert filters.get("date_from") == "2026-10-01"


def test_export_spanish_labels_and_readable_dates():
    assert ReportExportService._label("sales_count") == "Ventas"
    assert ReportExportService._label("date_from") == "Desde"
    assert ReportExportService._display_cell("2026-10-14T18:06:46.628041-04:00", "date") == "14/10/2026 18:06"
