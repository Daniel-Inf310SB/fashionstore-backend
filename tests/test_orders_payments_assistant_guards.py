from pathlib import Path

from app.services.reports.report_assistant_service import ReportAssistantService


def test_rejects_digital_as_order_status():
    assert ReportAssistantService._canonical_enum('orders-payments', 'order_status', 'digital') is None
    assert ReportAssistantService._canonical_enum('orders-payments', 'order_status', 'PAID') == 'PAID'


def test_rejects_unknown_payment_status():
    assert ReportAssistantService._canonical_enum('orders-payments', 'payment_status', 'electrónico') is None
    assert ReportAssistantService._canonical_enum('orders-payments', 'payment_status', 'APPROVED') == 'APPROVED'


def test_order_prompt_does_not_conflate_digital_and_status():
    from app.services.reports.report_assistant_prompt import ReportAssistantPrompt
    prompt = ReportAssistantPrompt.build('orders-payments')
    assert 'Compras digitales' in prompt
    assert 'NOT an order_status' in prompt
