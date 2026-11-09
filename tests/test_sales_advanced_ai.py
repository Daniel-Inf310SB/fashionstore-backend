from unittest.mock import patch
import pytest
from app.schemas.report_assistant import ReportAssistantRequest
from app.services.reports.report_assistant_service import ReportAssistantService

@pytest.mark.parametrize('command, expected', [
    ('Muéstrame los 10 productos más vendidos de octubre', 'top_products'),
    ('Compara las ventas por sucursal', 'branch_comparison'),
    ('Grafica las ventas por semana', 'weekly_sales'),
    ('Qué categorías generaron mayores ingresos', 'category_revenue'),
])
def test_infer_approved_sales_analysis_when_ai_does_not_return_it(command, expected):
    parsed = {'report_key': 'sales', 'action':'APPLY_FILTERS', 'mode':'replace', 'filters':{}}
    with patch('app.services.reports.report_assistant_service.OpenAIService.generate_json', return_value=(parsed, {})):
        response = ReportAssistantService.interpret(None, ReportAssistantRequest(command=command, current_report='sales'), tenant_id=1)
    assert response.analysis_kind == expected
    assert response.filters == {}


def test_unsupported_analysis_name_not_executed():
    parsed = {'report_key':'sales', 'action':'APPLY_FILTERS', 'mode':'replace', 'analysis_kind':'raw_sql', 'filters':{}}
    with patch('app.services.reports.report_assistant_service.OpenAIService.generate_json', return_value=(parsed, {})):
        response = ReportAssistantService.interpret(None, ReportAssistantRequest(command='Muéstrame las ventas', current_report='sales'), tenant_id=1)
    assert response.analysis_kind is None
