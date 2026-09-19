from __future__ import annotations

import html
import re
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy.orm import Session, joinedload

from app.models.audit_log import AuditLog
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product_variant import ProductVariant
from app.models.receipt import Receipt
from app.models.receipt_item import ReceiptItem
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User
from app.services.email_service import EmailService
from app.services.receipt_pdf_service import ReceiptPdfService


class ReceiptService:
    EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")

    @staticmethod
    def _receipt_number() -> str:
        return (
            f"REC-{datetime.now(timezone.utc).strftime('%Y%m%d')}-"
            f"{uuid4().hex[:10].upper()}"
        )

    @staticmethod
    def _full_name(user: User | None) -> str:
        if user is None:
            return "CONSUMIDOR FINAL"
        return f"{user.first_name} {user.last_name or ''}".strip()

    @staticmethod
    def _valid_email(value: str | None) -> bool:
        return bool(value and ReceiptService.EMAIL_RE.fullmatch(value.strip()))

    # =====================================================
    # VENTA PRESENCIAL
    # =====================================================

    @staticmethod
    def issue_sale_receipt(db: Session, *, current_user: User, sale_id: int):
        if current_user.role is None or current_user.role.name != "CAJERO":
            raise PermissionError(
                "Solo un cajero puede emitir el comprobante de una venta presencial."
            )

        sale = (
            db.query(Sale)
            .options(
                joinedload(Sale.customer),
                joinedload(Sale.items)
                .joinedload(SaleItem.product_variant)
                .joinedload(ProductVariant.product),
                joinedload(Sale.items)
                .joinedload(SaleItem.product_variant)
                .joinedload(ProductVariant.size),
                joinedload(Sale.items)
                .joinedload(SaleItem.product_variant)
                .joinedload(ProductVariant.color),
                joinedload(Sale.payments),
                joinedload(Sale.receipt),
            )
            .filter(Sale.id == sale_id)
            .first()
        )

        if sale is None:
            raise LookupError("La venta presencial no existe.")
        if sale.cashier_id != current_user.id:
            raise PermissionError(
                "No puedes emitir el comprobante de una venta de otro cajero."
            )
        if sale.status != "PAID":
            raise ValueError("Solo se puede emitir comprobante para una venta pagada.")
        if sale.receipt is not None:
            return sale.receipt

        payment = next(
            (
                value
                for value in sorted(sale.payments, key=lambda item: item.id, reverse=True)
                if value.status == "APPROVED"
            ),
            None,
        )
        if payment is None:
            raise ValueError("La venta no tiene un pago aprobado.")

        customer = sale.customer
        receipt = Receipt(
            receipt_number=ReceiptService._receipt_number(),
            receipt_type="IN_STORE_SALE",
            order_id=None,
            sale_id=sale.id,
            customer_name=ReceiptService._full_name(customer),
            customer_email=customer.email if customer else None,
            customer_document=customer.document_number if customer else None,
            subtotal=sale.subtotal,
            discount_amount=sale.discount_amount,
            total_amount=sale.total_amount,
            payment_method=payment.payment_method,
            currency=payment.currency,
            email_status="NOT_REQUESTED",
        )
        db.add(receipt)
        db.flush()

        for item in sale.items:
            variant = item.product_variant
            db.add(
                ReceiptItem(
                    receipt_id=receipt.id,
                    product_name=variant.product.name,
                    sku=variant.sku,
                    size_name=variant.size.name if variant.size else None,
                    color_name=variant.color.name if variant.color else None,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
            )

        db.add(
            AuditLog(
                user_id=current_user.id,
                action="CREATE",
                module="RECEIPTS",
                entity_type="Receipt",
                entity_id=receipt.id,
                description=(
                    f"Comprobante {receipt.receipt_number} emitido para {sale.sale_code}."
                ),
                old_values=None,
                new_values={"sale_id": sale.id, "total_amount": str(receipt.total_amount)},
                status="SUCCESS",
            )
        )
        db.commit()

        return (
            db.query(Receipt)
            .options(joinedload(Receipt.items))
            .filter(Receipt.id == receipt.id)
            .first()
        )

    # =====================================================
    # COMPRA DIGITAL - CREACION AUTOMATICA
    # =====================================================

    @staticmethod
    def issue_order_receipt(
        db: Session,
        *,
        order_id: int,
        payment_id: int,
    ) -> Receipt:
        existing = (
            db.query(Receipt)
            .options(joinedload(Receipt.items))
            .filter(Receipt.order_id == order_id)
            .first()
        )
        if existing is not None:
            return existing

        order = (
            db.query(Order)
            .options(
                joinedload(Order.customer),
                joinedload(Order.items)
                .joinedload(OrderItem.product_variant)
                .joinedload(ProductVariant.product),
                joinedload(Order.items)
                .joinedload(OrderItem.product_variant)
                .joinedload(ProductVariant.size),
                joinedload(Order.items)
                .joinedload(OrderItem.product_variant)
                .joinedload(ProductVariant.color),
            )
            .filter(Order.id == order_id)
            .first()
        )
        if order is None:
            raise LookupError("La compra digital no existe.")
        if order.status != "PAID":
            raise ValueError("Solo se genera comprobante para una compra pagada.")

        payment = (
            db.query(Payment)
            .filter(
                Payment.id == payment_id,
                Payment.order_id == order.id,
                Payment.status == "APPROVED",
            )
            .first()
        )
        if payment is None:
            raise ValueError("La compra no tiene el pago aprobado indicado.")

        customer = order.customer
        customer_email = customer.email if customer else None
        email_status = (
            "PENDING" if ReceiptService._valid_email(customer_email) else "NOT_REQUESTED"
        )

        receipt = Receipt(
            receipt_number=ReceiptService._receipt_number(),
            receipt_type="ONLINE_PURCHASE",
            order_id=order.id,
            sale_id=None,
            customer_name=ReceiptService._full_name(customer),
            customer_email=customer_email,
            customer_document=customer.document_number if customer else None,
            subtotal=order.subtotal,
            discount_amount=order.discount_amount,
            total_amount=order.total_amount,
            payment_method=payment.payment_method,
            currency=payment.currency,
            email_status=email_status,
        )
        db.add(receipt)
        db.flush()

        for item in order.items:
            variant = item.product_variant
            db.add(
                ReceiptItem(
                    receipt_id=receipt.id,
                    product_name=variant.product.name,
                    sku=variant.sku,
                    size_name=variant.size.name if variant.size else None,
                    color_name=variant.color.name if variant.color else None,
                    quantity=item.quantity,
                    unit_price=item.unit_price,
                    subtotal=item.subtotal,
                )
            )

        db.add(
            AuditLog(
                user_id=order.customer_id,
                action="CREATE",
                module="RECEIPTS",
                entity_type="Receipt",
                entity_id=receipt.id,
                description=(
                    f"Comprobante {receipt.receipt_number} generado automaticamente "
                    f"para {order.order_code}."
                ),
                old_values=None,
                new_values={
                    "order_id": order.id,
                    "payment_id": payment.id,
                    "total_amount": str(receipt.total_amount),
                    "email_status": receipt.email_status,
                },
                status="SUCCESS",
            )
        )
        db.commit()

        return (
            db.query(Receipt)
            .options(joinedload(Receipt.items))
            .filter(Receipt.id == receipt.id)
            .first()
        )

    @staticmethod
    def email_order_receipt(
        db: Session,
        *,
        receipt_id: int,
    ) -> Receipt:
        receipt = (
            db.query(Receipt)
            .options(joinedload(Receipt.items), joinedload(Receipt.order))
            .filter(Receipt.id == receipt_id)
            .first()
        )
        if receipt is None:
            raise LookupError("El comprobante no existe.")
        if receipt.receipt_type != "ONLINE_PURCHASE":
            raise ValueError("El comprobante no corresponde a una compra digital.")

        # Idempotencia: un webhook repetido no vuelve a enviar el correo.
        if receipt.email_status == "SENT":
            return receipt

        if not ReceiptService._valid_email(receipt.customer_email):
            receipt.email_status = "NOT_REQUESTED"
            db.commit()
            return receipt

        receipt.email_status = "PENDING"
        db.commit()

        try:
            pdf_bytes = ReceiptPdfService.generate(receipt)
            safe_name = html.escape(receipt.customer_name)
            order_code = receipt.order.order_code if receipt.order else "tu compra"
            safe_order_code = html.escape(order_code)
            safe_receipt_number = html.escape(receipt.receipt_number)

            EmailService.send_email(
                to_email=receipt.customer_email,
                to_name=receipt.customer_name,
                subject=f"Tu comprobante de compra {order_code}",
                html_content=f"""
                <!DOCTYPE html>
                <html lang="es">
                <body style="margin:0;padding:0;background:#f5f5f5;font-family:Arial,Helvetica,sans-serif;">
                    <table width="100%" cellspacing="0" cellpadding="0" style="padding:32px 16px;background:#f5f5f5;">
                        <tr>
                            <td align="center">
                                <table width="100%" cellspacing="0" cellpadding="0" style="max-width:600px;background:#ffffff;border-radius:16px;overflow:hidden;">
                                    <tr>
                                        <td style="background:#111111;color:#ffffff;padding:28px 32px;font-size:24px;font-weight:700;">
                                            FashionStore
                                        </td>
                                    </tr>
                                    <tr>
                                        <td style="padding:32px;color:#222222;">
                                            <h2 style="margin:0 0 16px;">Pago confirmado</h2>
                                            <p style="line-height:1.6;margin:0 0 12px;">Hola {safe_name}, tu compra <strong>{safe_order_code}</strong> fue pagada correctamente.</p>
                                            <p style="line-height:1.6;margin:0 0 12px;">Adjuntamos tu comprobante <strong>{safe_receipt_number}</strong> en formato PDF.</p>
                                            <p style="line-height:1.6;margin:0;color:#666666;">Gracias por comprar en FashionStore.</p>
                                        </td>
                                    </tr>
                                </table>
                            </td>
                        </tr>
                    </table>
                </body>
                </html>
                """,
                attachments=[
                    (f"{receipt.receipt_number}.pdf", pdf_bytes),
                ],
            )
        except Exception:
            receipt.email_status = "FAILED"
            receipt.emailed_at = None
            db.commit()
            raise

        receipt.email_status = "SENT"
        receipt.emailed_at = datetime.now(timezone.utc)
        db.add(
            AuditLog(
                user_id=receipt.order.customer_id if receipt.order else None,
                action="EMAIL",
                module="RECEIPTS",
                entity_type="Receipt",
                entity_id=receipt.id,
                description=(
                    f"Comprobante {receipt.receipt_number} enviado por correo al cliente."
                ),
                old_values={"email_status": "PENDING"},
                new_values={"email_status": "SENT"},
                status="SUCCESS",
            )
        )
        db.commit()
        db.refresh(receipt)
        return receipt

    @staticmethod
    def issue_and_email_order_receipt(
        db: Session,
        *,
        order_id: int,
        payment_id: int,
    ) -> Receipt:
        receipt = ReceiptService.issue_order_receipt(
            db,
            order_id=order_id,
            payment_id=payment_id,
        )
        return ReceiptService.email_order_receipt(db, receipt_id=receipt.id)

    @staticmethod
    def get_by_sale(db: Session, *, current_user: User, sale_id: int):
        receipt = (
            db.query(Receipt)
            .options(joinedload(Receipt.items), joinedload(Receipt.sale))
            .filter(Receipt.sale_id == sale_id)
            .first()
        )
        if receipt is None:
            raise LookupError("La venta todavia no tiene comprobante.")
        if current_user.role is None:
            raise PermissionError("Usuario sin rol.")
        if current_user.role.name == "ADMINISTRADOR":
            return receipt
        if current_user.role.name == "CAJERO" and receipt.sale.cashier_id == current_user.id:
            return receipt
        raise PermissionError("No puedes consultar este comprobante.")
