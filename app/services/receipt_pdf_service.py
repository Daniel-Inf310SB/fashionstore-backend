from __future__ import annotations

from io import BytesIO
from decimal import Decimal

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.models.receipt import Receipt


class ReceiptPdfService:
    @staticmethod
    def _money(value) -> str:
        return f"{Decimal(value or 0).quantize(Decimal('0.01')):.2f}"

    @staticmethod
    def generate(receipt: Receipt) -> bytes:
        """Genera el comprobante en memoria y devuelve sus bytes PDF."""
        buffer = BytesIO()

        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=18 * mm,
            leftMargin=18 * mm,
            topMargin=18 * mm,
            bottomMargin=18 * mm,
            title=f"Comprobante {receipt.receipt_number}",
            author="FashionStore",
        )

        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            "ReceiptTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            alignment=TA_CENTER,
            spaceAfter=4 * mm,
        )
        subtitle_style = ParagraphStyle(
            "ReceiptSubtitle",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
            textColor=colors.HexColor("#555555"),
            alignment=TA_CENTER,
            spaceAfter=7 * mm,
        )
        section_style = ParagraphStyle(
            "ReceiptSection",
            parent=styles["Heading3"],
            fontName="Helvetica-Bold",
            fontSize=11,
            leading=14,
            spaceBefore=2 * mm,
            spaceAfter=2 * mm,
        )
        normal = ParagraphStyle(
            "ReceiptNormal",
            parent=styles["Normal"],
            fontSize=9,
            leading=12,
        )
        right = ParagraphStyle(
            "ReceiptRight",
            parent=normal,
            alignment=TA_RIGHT,
        )

        story = [
            Paragraph("FashionStore", title_style),
            Paragraph("Comprobante de compra", subtitle_style),
            Paragraph("Datos del comprobante", section_style),
        ]

        issued_at = receipt.issued_at
        issued_text = issued_at.strftime("%d/%m/%Y %H:%M") if issued_at else "-"

        info = Table(
            [
                ["Nro. comprobante", receipt.receipt_number],
                ["Cliente", receipt.customer_name],
                ["Correo", receipt.customer_email or "-"],
                ["Documento", receipt.customer_document or "-"],
                ["Fecha", issued_text],
                ["Metodo de pago", receipt.payment_method],
                ["Moneda", receipt.currency],
            ],
            colWidths=[48 * mm, 106 * mm],
        )
        info.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTNAME", (1, 0), (1, -1), "Helvetica"),
                    ("FONTSIZE", (0, 0), (-1, -1), 9),
                    ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#222222")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#DDDDDD")),
                ]
            )
        )
        story.extend([info, Spacer(1, 6 * mm), Paragraph("Detalle", section_style)])

        rows = [["Producto", "Variante", "Cant.", "P. unit.", "Subtotal"]]
        for item in sorted(receipt.items, key=lambda value: value.id or 0):
            variant_parts = []
            if item.size_name:
                variant_parts.append(f"Talla: {item.size_name}")
            if item.color_name:
                variant_parts.append(f"Color: {item.color_name}")
            variant_parts.append(f"SKU: {item.sku}")

            rows.append(
                [
                    Paragraph(item.product_name, normal),
                    Paragraph("<br/>".join(variant_parts), normal),
                    str(item.quantity),
                    Paragraph(f"{ReceiptPdfService._money(item.unit_price)} {receipt.currency}", right),
                    Paragraph(f"{ReceiptPdfService._money(item.subtotal)} {receipt.currency}", right),
                ]
            )

        detail = Table(
            rows,
            colWidths=[52 * mm, 42 * mm, 15 * mm, 24 * mm, 27 * mm],
            repeatRows=1,
        )
        detail.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#111111")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 8),
                    ("ALIGN", (2, 1), (2, -1), "CENTER"),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#CCCCCC")),
                    ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F7F7F7")]),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        story.extend([detail, Spacer(1, 6 * mm)])

        totals = Table(
            [
                ["Subtotal", f"{ReceiptPdfService._money(receipt.subtotal)} {receipt.currency}"],
                ["Descuento", f"-{ReceiptPdfService._money(receipt.discount_amount)} {receipt.currency}"],
                ["TOTAL", f"{ReceiptPdfService._money(receipt.total_amount)} {receipt.currency}"],
            ],
            colWidths=[110 * mm, 50 * mm],
            hAlign="RIGHT",
        )
        totals.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (-1, 1), "Helvetica"),
                    ("FONTNAME", (0, 2), (-1, 2), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("ALIGN", (1, 0), (1, -1), "RIGHT"),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                    ("LINEABOVE", (0, 2), (-1, 2), 1, colors.HexColor("#111111")),
                ]
            )
        )
        story.extend(
            [
                totals,
                Spacer(1, 10 * mm),
                Paragraph(
                    "Gracias por tu compra. Este documento fue generado automaticamente por FashionStore.",
                    subtitle_style,
                ),
            ]
        )

        doc.build(story)
        return buffer.getvalue()
