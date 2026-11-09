from __future__ import annotations

from io import BytesIO
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape


class ReportExportService:
    MEDIA_TYPES = {
        "pdf": "application/pdf",
        "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }

    LABELS = {
        "date_from": "Desde", "date_to": "Hasta", "min_total": "Monto mínimo", "max_total": "Monto máximo",
        "sales_count": "Ventas", "units_sold": "Unidades vendidas", "gross_total": "Total vendido",
        "discount_total": "Descuentos", "average_ticket": "Ticket promedio", "payment_methods": "Métodos de pago",
        "variants_count": "Variantes", "stock_total": "Stock físico", "reserved_total": "Reservado",
        "available_total": "Disponible", "low_stock_count": "Stock bajo", "out_of_stock_count": "Agotados",
        "branch_id": "Sucursal", "customer_id": "Cliente", "product_id": "Producto", "category_id": "Categoría",
        "payment_method": "Método de pago", "status": "Estado", "search": "Búsqueda",
        "stock_state": "Estado de stock", "orders_count": "Cantidad de compras", "units": "Unidades",
        "orders_total": "Total de compras (Bs)", "approved_payments_total": "Pagos aprobados (Bs)",
        "by_order_status": "Por estado de compra", "by_payment_status": "Por estado de pago",
        "reservations_count": "Cantidad de reservas", "units_reserved": "Unidades reservadas",
        "estimated_total": "Total estimado (Bs)", "by_status": "Por estado",
        "order_status": "Estado de compra", "payment_status": "Estado de pago",
        "payment_statuses": "Estados de pago", "delivery_type": "Tipo de entrega",
        "groups_count": "Grupos analizados", "analysis_total": "Importe analizado (Bs)",
        "analysis_kind": "Tipo de análisis", "sales_count": "Ventas",

    }

    @staticmethod
    def _label(key: str) -> str:
        return ReportExportService.LABELS.get(key, key.replace("_", " ").capitalize())

    STATUS_LABELS = {
        "COMPLETED": "Completada", "PENDING_PAYMENT": "Pendiente de pago", "APPROVED": "Aprobado",
        "PENDING": "Pendiente", "PAID": "Pagada", "PROCESSING": "Procesando",
        "PAYMENT_FAILED": "Pago fallido", "PREPARING": "Preparando", "SHIPPED": "Enviada",
        "DELIVERED": "Entregada", "CANCELLED": "Cancelada", "REFUNDED": "Reembolsada",
        "REJECTED": "Rechazado", "FAILED": "Fallido", "EXPIRED": "Expirada",
        "PICKUP": "Recojo", "DELIVERY": "Envío", "IN_STOCK": "Disponible",
        "LOW_STOCK": "Stock bajo", "OUT_OF_STOCK": "Agotado", "CONFIRMED": "Confirmada",
        "READY": "Lista", "ATTENDED": "Atendida", "RESERVED": "Reservada",
    }

    @staticmethod
    def _readable(value: Any) -> str:
        if isinstance(value, str):
            return ReportExportService.STATUS_LABELS.get(value, value)
        return ReportExportService._value(value)

    @staticmethod
    def _display_cell(value: Any, key: str) -> str:
        if value is None:
            return "—"
        if key in {"date", "expires_at", "created_at", "updated_at"}:
            from datetime import datetime
            try:
                parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
                return parsed.strftime("%d/%m/%Y %H:%M")
            except (ValueError, TypeError):
                return str(value)
        if key in {"order_status", "status", "payment_status", "payment_statuses", "delivery_type", "stock_state", "item_status"}:
            if isinstance(value, str):
                return ", ".join(ReportExportService._readable(part.strip()) for part in value.split(","))
        return ReportExportService._value(value)

    @staticmethod
    def _value(value: Any) -> str:
        if value is None:
            return "—"
        if isinstance(value, float):
            return f"{value:,.2f}"
        if isinstance(value, bool):
            return "Sí" if value else "No"
        return str(value)

    @staticmethod
    def _filter_lines(report: dict[str, Any]) -> list[tuple[str, str]]:
        filters = report.get("filters") or {}
        if not filters:
            return [("Filtros", "Sin filtros")]
        return [(ReportExportService._label(key), ReportExportService._readable(value)) for key, value in filters.items()]

    @staticmethod
    def _summary_lines(report: dict[str, Any]) -> list[tuple[str, str]]:
        summary = report.get("summary") or {}
        rows: list[tuple[str, str]] = []
        for key, value in summary.items():
            label = ReportExportService._label(key)
            if isinstance(value, dict):
                text = ", ".join(f"{ReportExportService._readable(k)}: {v}" for k, v in value.items()) or "—"
            else:
                text = ReportExportService._value(value)
            rows.append((label, text))
        return rows

    @staticmethod
    def export(report: dict[str, Any], export_format: str) -> tuple[bytes, str, str]:
        normalized = export_format.lower().strip()
        if normalized == "pdf":
            content = ReportExportService.to_pdf(report)
        elif normalized == "xlsx":
            content = ReportExportService.to_excel(report)
        elif normalized == "docx":
            content = ReportExportService.to_word(report)
        else:
            raise ValueError("Formato no soportado. Use pdf, xlsx o docx.")

        return content, ReportExportService.MEDIA_TYPES[normalized], normalized

    @staticmethod
    def to_pdf(report: dict[str, Any]) -> bytes:
        try:
            from reportlab.lib import colors
            from reportlab.lib.enums import TA_CENTER
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import mm
            from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
        except ImportError as exc:
            raise RuntimeError("Falta instalar reportlab: pip install reportlab") from exc

        output = BytesIO()
        doc = SimpleDocTemplate(
            output,
            pagesize=landscape(A4),
            rightMargin=10 * mm,
            leftMargin=10 * mm,
            topMargin=10 * mm,
            bottomMargin=10 * mm,
            title=report["title"],
            author="FashionStore",
        )
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReportTitle",
            parent=styles["Title"],
            alignment=TA_CENTER,
            fontSize=18,
            leading=22,
            spaceAfter=8,
        )
        small = ParagraphStyle("ReportSmall", parent=styles["BodyText"], fontSize=6.2, leading=7.5)
        header_small = ParagraphStyle("ReportHeaderSmall", parent=small, textColor=colors.white)
        meta = ParagraphStyle("ReportMeta", parent=styles["BodyText"], fontSize=8.5, leading=10)

        story: list[Any] = [
            Paragraph("FashionStore", title_style),
            Paragraph(escape(report["title"]), styles["Heading2"]),
            Paragraph(f"Generado: {escape(ReportExportService._display_cell(report['generated_at'], "created_at"))}", meta),
            Spacer(1, 5 * mm),
        ]

        filter_data = [["Filtros aplicados", "Valor"]] + [list(row) for row in ReportExportService._filter_lines(report)]
        filter_table = Table(filter_data, colWidths=[55 * mm, 200 * mm], repeatRows=1)
        filter_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9D9D9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
        ]))
        story += [filter_table, Spacer(1, 5 * mm)]

        summary_data = [["Resumen", "Valor"]] + [list(row) for row in ReportExportService._summary_lines(report)]
        summary_table = Table(summary_data, colWidths=[75 * mm, 180 * mm], repeatRows=1)
        summary_table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#4338CA")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, -1), 8),
            ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D9D9D9")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ]))
        story += [summary_table, Spacer(1, 6 * mm)]

        columns = report.get("columns") or []
        header = [Paragraph(f"<b>{escape(col['label'])}</b>", header_small) for col in columns]
        data: list[list[Any]] = [header]
        for row in report.get("rows") or []:
            data.append([
                Paragraph(escape(ReportExportService._display_cell(row.get(col["key"]), col["key"])), small)
                for col in columns
            ])

        if len(data) == 1:
            data.append([Paragraph("Sin resultados", small)] + [""] * max(0, len(columns) - 1))

        page_width = landscape(A4)[0] - 20 * mm
        if report.get("report_key") == "orders-payments" and len(columns) == 12:
            # Priorizar producto, sucursal y estado; columnas numéricas son más estrechas.
            weights = [1.3, 1.25, 1.5, 1.15, 1.15, .75, 1.7, .55, .8, 1.0, .95, .95]
            total_weight = sum(weights)
            widths = [page_width * weight / total_weight for weight in weights]
        else:
            widths = [page_width / max(1, len(columns))] * len(columns)
        table = Table(data, colWidths=widths, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#D0D0D0")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 3),
            ("RIGHTPADDING", (0, 0), (-1, -1), 3),
            ("TOPPADDING", (0, 0), (-1, -1), 3),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F8F8F8")]),
        ]))
        story.append(table)
        doc.build(story)
        return output.getvalue()

    @staticmethod
    def to_excel(report: dict[str, Any]) -> bytes:
        try:
            from openpyxl import Workbook
            from openpyxl.styles import Alignment, Font, PatternFill
            from openpyxl.utils import get_column_letter
        except ImportError as exc:
            raise RuntimeError("Falta instalar openpyxl: pip install openpyxl") from exc

        wb = Workbook()
        ws = wb.active
        ws.title = "Reporte"

        ws["A1"] = "FashionStore"
        ws["A1"].font = Font(size=18, bold=True)
        ws["A2"] = report["title"]
        ws["A2"].font = Font(size=14, bold=True)
        ws["A3"] = f"Generado: {ReportExportService._display_cell(report['generated_at'], 'created_at')}"

        row_index = 5
        ws.cell(row=row_index, column=1, value="FILTROS APLICADOS").font = Font(bold=True)
        row_index += 1
        for label, value in ReportExportService._filter_lines(report):
            ws.cell(row=row_index, column=1, value=label)
            ws.cell(row=row_index, column=2, value=value)
            row_index += 1

        row_index += 1
        ws.cell(row=row_index, column=1, value="RESUMEN").font = Font(bold=True)
        row_index += 1
        for label, value in ReportExportService._summary_lines(report):
            ws.cell(row=row_index, column=1, value=label)
            ws.cell(row=row_index, column=2, value=value)
            row_index += 1

        row_index += 2
        table_header_row = row_index
        columns = report.get("columns") or []
        header_fill = PatternFill("solid", fgColor="111111")
        for col_index, column in enumerate(columns, start=1):
            cell = ws.cell(row=row_index, column=col_index, value=column["label"])
            cell.font = Font(color="FFFFFF", bold=True)
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

        for data_row in report.get("rows") or []:
            row_index += 1
            for col_index, column in enumerate(columns, start=1):
                value = data_row.get(column["key"])
                display = ReportExportService._display_cell(value, column["key"])
                # Preserve numeric cells so Excel can sum/filter monetary amounts.
                formatted = value if isinstance(value, (int, float)) and not isinstance(value, bool) else display
                cell = ws.cell(row=row_index, column=col_index, value=formatted)
                if isinstance(formatted, float):
                    cell.number_format = '#,##0.00'
                cell.alignment = Alignment(vertical="top", wrap_text=True)

        ws.freeze_panes = f"A{table_header_row + 1}"
        if columns:
            ws.auto_filter.ref = f"A{table_header_row}:{get_column_letter(len(columns))}{row_index}"

        for col_index, column in enumerate(columns, start=1):
            max_len = len(column["label"])
            for r in range(table_header_row + 1, row_index + 1):
                value = ws.cell(r, col_index).value
                if value is not None:
                    max_len = max(max_len, len(str(value)))
            ws.column_dimensions[get_column_letter(col_index)].width = min(max(max_len + 2, 12), 38)

        output = BytesIO()
        wb.save(output)
        return output.getvalue()

    @staticmethod
    def to_word(report: dict[str, Any]) -> bytes:
        try:
            from docx import Document
            from docx.enum.section import WD_ORIENT, WD_SECTION_START
            from docx.enum.table import WD_TABLE_ALIGNMENT, WD_CELL_VERTICAL_ALIGNMENT
            from docx.enum.text import WD_ALIGN_PARAGRAPH
            from docx.shared import Inches, Pt
        except ImportError as exc:
            raise RuntimeError("Falta instalar python-docx: pip install python-docx") from exc

        doc = Document()
        section = doc.sections[0]
        section.orientation = WD_ORIENT.LANDSCAPE
        section.page_width, section.page_height = section.page_height, section.page_width
        # Wider paper for reports with twelve data columns; prevents broken identifiers.
        if len(report.get("columns") or []) >= 10:
            section.page_width = Inches(16.54)
            section.page_height = Inches(11.69)
        section.top_margin = Inches(0.45)
        section.bottom_margin = Inches(0.45)
        section.left_margin = Inches(0.45)
        section.right_margin = Inches(0.45)

        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        run = p.add_run("FashionStore")
        run.bold = True
        run.font.size = Pt(18)

        heading = doc.add_heading(report["title"], level=1)
        heading.alignment = WD_ALIGN_PARAGRAPH.CENTER
        doc.add_paragraph(f"Generado: {ReportExportService._display_cell(report['generated_at'], 'created_at')}")

        doc.add_heading("Filtros aplicados", level=2)
        filters_table = doc.add_table(rows=1, cols=2)
        filters_table.style = "Table Grid"
        filters_table.rows[0].cells[0].text = "Filtro"
        filters_table.rows[0].cells[1].text = "Valor"
        for label, value in ReportExportService._filter_lines(report):
            cells = filters_table.add_row().cells
            cells[0].text = label
            cells[1].text = value

        doc.add_heading("Resumen", level=2)
        summary_table = doc.add_table(rows=1, cols=2)
        summary_table.style = "Table Grid"
        summary_table.rows[0].cells[0].text = "Indicador"
        summary_table.rows[0].cells[1].text = "Valor"
        for label, value in ReportExportService._summary_lines(report):
            cells = summary_table.add_row().cells
            cells[0].text = label
            cells[1].text = value

        doc.add_heading("Detalle", level=2)
        columns = report.get("columns") or []
        detail = doc.add_table(rows=1, cols=max(1, len(columns)))
        detail.style = "Table Grid"
        detail.alignment = WD_TABLE_ALIGNMENT.CENTER
        detail.autofit = False
        if columns:
            if report.get("report_key") == "orders-payments" and len(columns) == 12:
                widths = [1.30, 1.15, 1.45, 1.30, 1.35, .8, 1.60, .72, 1.05, 1.15, 1.00, 1.00]
            else:
                usable = section.page_width.inches - section.left_margin.inches - section.right_margin.inches
                widths = [usable / len(columns)] * len(columns)
            for index, width in enumerate(widths):
                detail.columns[index].width = Inches(width)
        if columns:
            for index, column in enumerate(columns):
                detail.rows[0].cells[index].text = column["label"]
                detail.rows[0].cells[index].width = Inches(widths[index])
            for data_row in report.get("rows") or []:
                cells = detail.add_row().cells
                for index, column in enumerate(columns):
                    cells[index].text = ReportExportService._display_cell(data_row.get(column["key"]), column["key"])
                    cells[index].width = Inches(widths[index])
        else:
            detail.rows[0].cells[0].text = "Sin datos"

        for table in [filters_table, summary_table, detail]:
            for row in table.rows:
                for cell in row.cells:
                    for paragraph in cell.paragraphs:
                        for run in paragraph.runs:
                            run.font.size = Pt(7.5 if table is not detail else 7)
                    cell.vertical_alignment = WD_CELL_VERTICAL_ALIGNMENT.CENTER

        output = BytesIO()
        doc.save(output)
        return output.getvalue()
