from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.audit_log import AuditLog
from app.models.employee_branch import EmployeeBranch
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.payment import Payment
from app.models.sale import Sale
from app.models.user import User

from app.schemas.cash_payment import CashDeskPaymentCreate


class CashPaymentService:

    # =====================================================
    # DINERO
    # =====================================================

    @staticmethod
    def _money(
        value,
    ) -> Decimal:

        return Decimal(
            value or 0
        ).quantize(
            Decimal("0.01")
        )


    # =====================================================
    # PROCESAR PAGO EN CAJA
    # CU36 - GESTIONAR PAGO EN CAJA
    # =====================================================

    @staticmethod
    def process(
        db: Session,
        *,
        current_user: User,
        sale_id: int,
        data: CashDeskPaymentCreate,
    ):

        # =================================================
        # 1. VALIDAR ROL
        # =================================================

        if (
            current_user.role is None
            or current_user.role.name != "CAJERO"
        ):

            raise PermissionError(
                "Solo un cajero puede procesar pagos en caja."
            )


        # =================================================
        # 2. OBTENER SUCURSAL ACTIVA DEL CAJERO
        # =================================================

        assignment = (
            db.query(
                EmployeeBranch
            )
            .filter(
                EmployeeBranch.user_id
                == current_user.id,

                EmployeeBranch.is_active.is_(
                    True
                ),
            )
            .first()
        )

        if assignment is None:

            raise PermissionError(
                "El cajero no tiene una sucursal activa asignada."
            )


        # =================================================
        # 3. BLOQUEAR ÚNICAMENTE LA VENTA
        #
        # IMPORTANTE:
        # NO usar joinedload(Sale.items) junto con
        # with_for_update().
        #
        # PostgreSQL no permite FOR UPDATE sobre el lado
        # nullable de un LEFT OUTER JOIN.
        # =================================================

        sale = (
            db.query(
                Sale
            )
            .filter(
                Sale.id
                == sale_id
            )
            .with_for_update(
                of=Sale
            )
            .first()
        )

        if sale is None:

            raise LookupError(
                "La venta presencial no existe."
            )


        # =================================================
        # 4. VALIDAR PROPIEDAD DE LA VENTA
        # =================================================

        if (
            sale.cashier_id
            != current_user.id
            or sale.branch_id
            != assignment.branch_id
        ):

            raise PermissionError(
                "No puedes cobrar esta venta."
            )


        # =================================================
        # 5. VALIDAR ESTADO
        # =================================================

        if sale.status != "PENDING":

            raise ValueError(
                "La venta no está pendiente de pago."
            )


        # =================================================
        # 6. VALIDAR QUE NO EXISTA PAGO APROBADO
        #
        # La fila de Sale ya está bloqueada, por lo tanto
        # otro proceso que intente cobrar la misma venta
        # deberá esperar.
        # =================================================

        approved_payment = (
            db.query(
                Payment
            )
            .filter(
                Payment.sale_id
                == sale.id,

                Payment.status
                == "APPROVED",
            )
            .first()
        )

        if approved_payment is not None:

            raise ValueError(
                "La venta ya tiene un pago aprobado."
            )


        # =================================================
        # 7. CARGAR ÍTEMS DE LA VENTA
        #
        # Se hace DESPUÉS del FOR UPDATE para evitar el
        # OUTER JOIN que producía el error de PostgreSQL.
        # =================================================

        sale_items = list(
            sale.items
        )

        if not sale_items:

            raise ValueError(
                "La venta no contiene productos."
            )


        # =================================================
        # 8. TOTAL
        # =================================================

        total = (
            CashPaymentService._money(
                sale.total_amount
            )
        )

        received = None

        change = Decimal(
            "0.00"
        )


        # =================================================
        # 9. VALIDAR EFECTIVO
        # =================================================

        if (
            data.payment_method
            == "CASH"
        ):

            if (
                data.amount_received
                is None
            ):

                raise ValueError(
                    "Debes indicar el monto recibido para un pago en efectivo."
                )

            received = (
                CashPaymentService._money(
                    data.amount_received
                )
            )

            if received < total:

                raise ValueError(
                    "El monto recibido es menor al total de la venta."
                )

            change = (
                CashPaymentService._money(
                    received - total
                )
            )


        # =================================================
        # 10. VARIANTES INVOLUCRADAS
        # =================================================

        variant_ids = list(
            {
                item.product_variant_id
                for item in sale_items
            }
        )


        # =================================================
        # 11. BLOQUEAR INVENTARIO
        #
        # Esto evita que dos ventas descuenten simultáneamente
        # el mismo stock sin revalidarlo.
        # =================================================

        inventories = (
            db.query(
                Inventory
            )
            .filter(
                Inventory.branch_id
                == sale.branch_id,

                Inventory.product_variant_id.in_(
                    variant_ids
                ),

                Inventory.is_active.is_(
                    True
                ),
            )
            .with_for_update()
            .all()
        )


        inventory_map = {
            inventory.product_variant_id:
                inventory

            for inventory
            in inventories
        }


        # =================================================
        # 12. REVALIDAR STOCK
        # =================================================

        for item in sale_items:

            inventory = (
                inventory_map.get(
                    item.product_variant_id
                )
            )

            if inventory is None:

                raise ValueError(
                    "No existe inventario para la variante "
                    f"{item.product_variant_id}."
                )

            if (
                inventory.available_quantity
                < item.quantity
            ):

                raise ValueError(
                    "Stock insuficiente para completar la venta. "
                    f"Variante {item.product_variant_id}, "
                    f"disponible {inventory.available_quantity}."
                )


        # =================================================
        # 13. CREAR PAGO
        # =================================================

        now = datetime.now(
            timezone.utc
        )

        payment = Payment(
            payment_code=(
                f"PAY-"
                f"{now.strftime('%Y%m%d')}-"
                f"{uuid4().hex[:10].upper()}"
            ),

            sale_id=
                sale.id,

            order_id=
                None,

            user_id=
                current_user.id,

            payment_method=
                data.payment_method,

            channel=
                "CASH_DESK",

            provider=
                data.provider,

            amount=
                total,

            currency=
                "BOB",

            status=
                "APPROVED",

            external_transaction_id=
                data.external_transaction_id,

            external_reference=
                data.external_reference,

            paid_at=
                now,
        )

        db.add(
            payment
        )

        db.flush()


        # =================================================
        # 14. DESCONTAR INVENTARIO
        # =================================================

        for item in sale_items:

            inventory = (
                inventory_map[
                    item.product_variant_id
                ]
            )

            stock_before = (
                inventory.stock_quantity
            )

            reserved_before = (
                inventory.reserved_quantity
            )

            inventory.stock_quantity = (
                stock_before
                - item.quantity
            )


            # =============================================
            # MOVIMIENTO DE INVENTARIO
            # =============================================

            movement = InventoryMovement(
                inventory_id=
                    inventory.id,

                movement_type=
                    "SALE",

                quantity=
                    item.quantity,

                stock_before=
                    stock_before,

                stock_after=
                    inventory.stock_quantity,

                reserved_before=
                    reserved_before,

                reserved_after=
                    reserved_before,

                user_id=
                    current_user.id,

                reference_type=
                    "SALE",

                reference_id=
                    sale.id,

                reference_code=
                    sale.sale_code,

                reason=
                    "Venta presencial",
            )

            db.add(
                movement
            )


        # =================================================
        # 15. MARCAR VENTA COMO PAGADA
        # =================================================

        sale.status = (
            "PAID"
        )


        # =================================================
        # 16. AUDITORÍA
        # =================================================

        audit = AuditLog(
            user_id=
                current_user.id,

            action=
                "PAY",

            module=
                "SALES",

            entity_type=
                "Sale",

            entity_id=
                sale.id,

            description=(
                "Pago de caja aprobado para "
                f"{sale.sale_code}."
            ),

            old_values={
                "status":
                    "PENDING",
            },

            new_values={
                "status":
                    "PAID",

                "payment_id":
                    payment.id,

                "payment_method":
                    payment.payment_method,
            },

            status=
                "SUCCESS",
        )

        db.add(
            audit
        )


        # =================================================
        # 17. COMMIT
        # =================================================

        db.commit()

        db.refresh(
            payment
        )

        db.refresh(
            sale
        )


        # =================================================
        # 18. RESPUESTA
        # =================================================

        return {
            "id":
                payment.id,

            "payment_code":
                payment.payment_code,

            "sale_id":
                sale.id,

            "user_id":
                payment.user_id,

            "payment_method":
                payment.payment_method,

            "channel":
                "CASH_DESK",

            "provider":
                payment.provider,

            "amount":
                CashPaymentService._money(
                    payment.amount
                ),

            "amount_received":
                received,

            "change_amount":
                change,

            "currency":
                payment.currency,

            "status":
                "APPROVED",

            "external_transaction_id":
                payment.external_transaction_id,

            "external_reference":
                payment.external_reference,

            "paid_at":
                payment.paid_at,

            "created_at":
                payment.created_at,
        }