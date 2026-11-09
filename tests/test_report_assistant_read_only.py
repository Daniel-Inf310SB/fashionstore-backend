from unittest.mock import patch

import pytest

from app.schemas.report_assistant import ReportAssistantRequest
from app.services.reports.report_assistant_service import ReportAssistantService


@pytest.mark.parametrize("command", [
    "Elimina todas las ventas",
    "Borra los productos",
    "Modifica los precios",
    "Cancela las reservas",
    "Crea una compra",
])
def test_mutating_commands_rejected_before_calling_ai(command):
    with patch("app.services.reports.report_assistant_service.OpenAIService.generate_json") as ai:
        reply = ReportAssistantService.interpret(None, ReportAssistantRequest(command=command, current_report="sales"), tenant_id=1)
        assert reply.can_execute is False
        assert reply.filters == {}
        assert "no puede modificar" in reply.message
        ai.assert_not_called()


@pytest.mark.parametrize("command", [
    "Muéstrame las ventas de octubre",
    "Reporte de ventas canceladas",
    "Compara las ventas por sucursal",
    "Cuántos pedidos están pendientes",
])
def test_read_only_queries_are_not_blocked(command):
    assert ReportAssistantService._unsafe_command(command) is False
