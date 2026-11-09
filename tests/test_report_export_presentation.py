from io import BytesIO
from docx import Document
from openpyxl import load_workbook
from app.services.reports.export_service import ReportExportService


def test_word_excel_human_readable_statuses_dates_and_numeric_amounts():
    keys = ['code', 'date', 'branch', 'customer', 'order_status', 'delivery_type', 'products', 'units', 'payment_method', 'payment_statuses', 'approved_amount', 'total']
    report = {
        'title': 'Reporte de compras digitales y pagos',
        'report_key': 'orders-payments',
        'generated_at': '2026-10-20T05:19:45+00:00',
        'filters': {'date_from': '2026-10-01', 'date_to': '2026-10-31'},
        'summary': {'orders_count': 1, 'approved_payments_total': 130.0},
        'columns': [{'key': key, 'label': key} for key in keys],
        'rows': [dict(zip(keys, ['DEMO-1', '2026-10-14T18:06:46.628041-04:00', 'FashionStore', 'Cliente 01', 'PENDING_PAYMENT', 'PICKUP', 'Producto', 1, 'QR', 'APPROVED', 130.0, 130.0]))],
    }
    word = Document(BytesIO(ReportExportService.to_word(report)))
    texts = [cell.text for cell in word.tables[-1].rows[-1].cells]
    assert texts[1] == '14/10/2026 18:06'
    assert texts[4] == 'Pendiente de pago'
    assert texts[5] == 'Recojo'
    assert texts[9] == 'Aprobado'
    assert word.sections[0].page_width.inches > 16

    wb = load_workbook(BytesIO(ReportExportService.to_excel(report)))
    values = [cell.value for cell in list(wb.active.rows)[-1]][:len(keys)]
    assert values[1] == '14/10/2026 18:06'
    assert values[4] == 'Pendiente de pago'
    assert values[5] == 'Recojo'
    assert values[9] == 'Aprobado'
    assert values[10] == 130.0
    assert values[11] == 130.0
