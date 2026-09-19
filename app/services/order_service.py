from __future__ import annotations

import math

from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import String, cast, or_, select
from sqlalchemy.orm import Session, joinedload

from app.core.config import settings
from app.models.audit_log import AuditLog
from app.models.branch import Branch
from app.models.cart_item import CartItem
from app.models.employee_branch import EmployeeBranch
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.order import Order
from app.models.order_item import OrderItem
from app.models.payment import Payment
from app.models.product_variant import ProductVariant
from app.models.shopping_cart import ShoppingCart
from app.models.user import User
from app.schemas.order import OrderCreate
from app.services.customer_pricing import CustomerPricingService
from app.services.notification_service import NotificationService


class OrderService:

    ADMIN_ROLE = "ADMINISTRADOR"
    MANAGER_ROLE = "ENCARGADO_SUCURSAL"
    CUSTOMER_ROLE = "CLIENTE"

    # =====================================================
    # HELPERS
    # =====================================================

    @staticmethod
    def _money(value) -> Decimal:
        return Decimal(value or 0).quantize(Decimal("0.01"))

    @staticmethod
    def _role_name(user: User) -> str | None:
        return user.role.name if user.role is not None else None

    @staticmethod
    def _allowed_transitions(order: Order) -> list[str]:
        if order.status in {"PENDING_PAYMENT", "PAYMENT_FAILED"}:
            return ["CANCELLED"]

        if order.status == "PAID":
            return ["PREPARING"]

        if order.status == "PREPARING":
            if order.delivery_type == "PICKUP":
                return ["READY_FOR_PICKUP"]
            return ["SHIPPED"]

        if order.status == "READY_FOR_PICKUP":
            return ["COMPLETED"]

        if order.status == "SHIPPED":
            return ["DELIVERED"]

        if order.status == "DELIVERED":
            return ["COMPLETED"]

        return []

    @staticmethod
    def _base_query(db: Session):
        return (
            db.query(Order)
            .options(
                joinedload(Order.customer),
                joinedload(Order.branch),
                joinedload(Order.items)
                .joinedload(OrderItem.product_variant)
                .joinedload(ProductVariant.product),
                joinedload(Order.items)
                .joinedload(OrderItem.product_variant)
                .joinedload(ProductVariant.size),
                joinedload(Order.items)
                .joinedload(OrderItem.product_variant)
                .joinedload(ProductVariant.color),
                joinedload(Order.payments),
                joinedload(Order.receipt),
            )
        )

    @staticmethod
    def _get_order(db: Session, order_id: int) -> Order:
        order = (
            OrderService._base_query(db)
            .filter(Order.id == order_id)
            .first()
        )

        if order is None:
            raise LookupError("La compra digital no existe.")

        return order

    @staticmethod
    def _get_active_manager_branch(
        db: Session,
        current_user: User,
    ) -> int:
        assignment = (
            db.query(EmployeeBranch)
            .filter(
                EmployeeBranch.user_id == current_user.id,
                EmployeeBranch.is_active.is_(True),
            )
            .first()
        )

        if assignment is None:
            raise PermissionError(
                "El encargado no tiene una sucursal activa asignada."
            )

        return assignment.branch_id

    @staticmethod
    def _validate_order_access(
        db: Session,
        *,
        order: Order,
        current_user: User,
    ) -> None:
        role = OrderService._role_name(current_user)

        if role == OrderService.ADMIN_ROLE:
            return

        if role == OrderService.CUSTOMER_ROLE:
            if order.customer_id != current_user.id:
                raise PermissionError(
                    "No puedes acceder a la compra de otro cliente."
                )
            return

        if role == OrderService.MANAGER_ROLE:
            manager_branch_id = OrderService._get_active_manager_branch(
                db,
                current_user,
            )

            if order.branch_id != manager_branch_id:
                raise PermissionError(
                    "No puedes acceder a compras de otra sucursal."
                )
            return

        raise PermissionError(
            "Tu rol no puede consultar compras digitales."
        )

    @staticmethod
    def _generate_order_code() -> str:
        date_part = datetime.now(timezone.utc).strftime("%Y%m%d")
        random_part = uuid4().hex[:10].upper()
        return f"ORD-{date_part}-{random_part}"

    @staticmethod
    def _serialize(order: Order) -> dict:
        sorted_items = sorted(order.items, key=lambda item: item.id)
        sorted_payments = sorted(
            order.payments,
            key=lambda payment: payment.id,
        )

        total_units = sum(item.quantity for item in sorted_items)

        created_at = order.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=timezone.utc)

        payment_expires_at = created_at + timedelta(
            minutes=settings.order_payment_ttl_minutes
        )

        return {
            "id": order.id,
            "order_code": order.order_code,
            "customer_id": order.customer_id,
            "branch_id": order.branch_id,
            "status": order.status,
            "subtotal": OrderService._money(order.subtotal),
            "discount_amount": OrderService._money(
                order.discount_amount
            ),
            "total_amount": OrderService._money(order.total_amount),
            "delivery_type": order.delivery_type,
            "shipping_address": order.shipping_address,
            "tracking_code": order.tracking_code,
            "paid_at": order.paid_at,
            "ready_for_pickup_at": order.ready_for_pickup_at,
            "shipped_at": order.shipped_at,
            "delivered_at": order.delivered_at,
            "completed_at": order.completed_at,
            "cancelled_at": order.cancelled_at,
            "payment_expires_at": payment_expires_at,
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "total_items": len(sorted_items),
            "total_units": total_units,
            "customer": order.customer,
            "branch": order.branch,
            "items": sorted_items,
            "payments": sorted_payments,
            "receipt": order.receipt,
            "allowed_transitions": OrderService._allowed_transitions(order),
        }

    @staticmethod
    def _create_audit_log(
        db: Session,
        *,
        current_user: User,
        order: Order,
        action: str,
        description: str,
    ) -> None:
        db.add(
            AuditLog(
                user_id=current_user.id,
                action=action,
                module="ORDERS",
                entity_type="Order",
                entity_id=order.id,
                description=description,
                old_values=None,
                new_values={
                    "order_code": order.order_code,
                    "customer_id": order.customer_id,
                    "branch_id": order.branch_id,
                    "status": order.status,
                    "total_amount": str(order.total_amount),
                },
                status="SUCCESS",
            )
        )

    # =====================================================
    # CU33 - CREAR COMPRA DIGITAL DESDE CARRITO
    # =====================================================

    @staticmethod
    def create_order(
        db: Session,
        *,
        current_user: User,
        data: OrderCreate,
    ) -> dict:
        if OrderService._role_name(current_user) != OrderService.CUSTOMER_ROLE:
            raise PermissionError(
                "Solo un cliente puede realizar una compra digital."
            )

        cart = (
            db.query(ShoppingCart)
            .options(
                joinedload(ShoppingCart.items)
                .joinedload(CartItem.product_variant)
                .joinedload(ProductVariant.product),
                joinedload(ShoppingCart.items)
                .joinedload(CartItem.product_variant)
                .joinedload(ProductVariant.size),
                joinedload(ShoppingCart.items)
                .joinedload(CartItem.product_variant)
                .joinedload(ProductVariant.color),
            )
            .filter(ShoppingCart.id == data.cart_id)
            .first()
        )

        if cart is None:
            raise LookupError("El carrito no existe.")

        if cart.customer_id != current_user.id:
            raise PermissionError(
                "No puedes convertir el carrito de otro cliente."
            )

        if cart.status != "ACTIVE":
            raise ValueError(
                "El carrito ya fue convertido o no se encuentra activo."
            )

        if cart.branch_id is None:
            raise ValueError(
                "Debes seleccionar una sucursal antes de comprar."
            )

        if not cart.items:
            raise ValueError("El carrito está vacío.")

        branch = (
            db.query(Branch)
            .filter(
                Branch.id == cart.branch_id,
                Branch.is_active.is_(True),
            )
            .first()
        )

        if branch is None:
            raise ValueError(
                "La sucursal seleccionada no existe o está inactiva."
            )

        # Bloqueamos las filas de inventario que participarán en la compra.
        variant_ids = [item.product_variant_id for item in cart.items]

        inventories = (
            db.query(Inventory)
            .filter(
                Inventory.branch_id == cart.branch_id,
                Inventory.product_variant_id.in_(variant_ids),
                Inventory.is_active.is_(True),
            )
            .with_for_update()
            .all()
        )

        inventory_by_variant = {
            inventory.product_variant_id: inventory
            for inventory in inventories
        }

        product_ids = list({
            item.product_variant.product_id
            for item in cart.items
            if item.product_variant is not None and item.product_variant.product is not None
        })
        promotions_by_product = CustomerPricingService.get_active_promotions_by_product(
            db, product_ids
        )

        subtotal = Decimal("0.00")
        discounted_total = Decimal("0.00")
        prepared_items: list[tuple[CartItem, Decimal, Decimal]] = []

        for cart_item in cart.items:
            variant = cart_item.product_variant

            if variant is None or not variant.is_active:
                raise ValueError(
                    "Una de las variantes del carrito ya no está disponible."
                )

            if variant.product is None or not variant.product.is_active:
                raise ValueError(
                    "Uno de los productos del carrito ya no está disponible."
                )

            inventory = inventory_by_variant.get(
                cart_item.product_variant_id
            )

            if inventory is None:
                raise ValueError(
                    f"No existe inventario para la variante "
                    f"{variant.sku} en la sucursal seleccionada."
                )

            available_quantity = (
                inventory.stock_quantity - inventory.reserved_quantity
            )

            if available_quantity < cart_item.quantity:
                raise ValueError(
                    f"Stock insuficiente para {variant.product.name} "
                    f"({variant.sku}). Disponible: {available_quantity}."
                )

            original_unit_price = OrderService._money(
                Decimal(variant.product.base_price or 0)
                + Decimal(variant.additional_price or 0)
            )
            applied_promotion = CustomerPricingService.choose_best_promotion(
                promotions_by_product.get(variant.product_id),
                original_unit_price,
            )
            unit_price = CustomerPricingService.apply_discount(
                original_unit_price,
                applied_promotion,
            )
            original_item_subtotal = OrderService._money(
                original_unit_price * cart_item.quantity
            )
            item_subtotal = OrderService._money(
                unit_price * cart_item.quantity
            )
            subtotal += original_item_subtotal
            discounted_total += item_subtotal
            prepared_items.append(
                (cart_item, unit_price, item_subtotal)
            )

        subtotal = OrderService._money(subtotal)
        discounted_total = OrderService._money(discounted_total)
        discount_amount = OrderService._money(subtotal - discounted_total)
        total_amount = discounted_total

        shipping_address = (data.shipping_address or "").strip() or None
        if data.delivery_type == "DELIVERY" and not shipping_address:
            raise ValueError("Debes indicar una dirección para envío a domicilio.")

        try:
            order = Order(
                order_code=OrderService._generate_order_code(),
                customer_id=current_user.id,
                branch_id=cart.branch_id,
                status="PENDING_PAYMENT",
                subtotal=subtotal,
                discount_amount=discount_amount,
                total_amount=total_amount,
                delivery_type=data.delivery_type,
                shipping_address=shipping_address,
            )

            db.add(order)
            db.flush()

            for cart_item, unit_price, item_subtotal in prepared_items:
                db.add(
                    OrderItem(
                        order_id=order.id,
                        product_variant_id=cart_item.product_variant_id,
                        quantity=cart_item.quantity,
                        unit_price=unit_price,
                        subtotal=item_subtotal,
                    )
                )

                inventory = inventory_by_variant[
                    cart_item.product_variant_id
                ]

                reserved_before = inventory.reserved_quantity
                reserved_after = reserved_before + cart_item.quantity
                inventory.reserved_quantity = reserved_after

                db.add(
                    InventoryMovement(
                        inventory_id=inventory.id,
                        movement_type="RESERVE",
                        quantity=cart_item.quantity,
                        stock_before=inventory.stock_quantity,
                        stock_after=inventory.stock_quantity,
                        reserved_before=reserved_before,
                        reserved_after=reserved_after,
                        supplier_id=None,
                        user_id=current_user.id,
                        unit_cost=None,
                        reference_type="ORDER",
                        reference_id=order.id,
                        reference_code=order.order_code,
                        reason="Stock reservado para compra digital pendiente de pago.",
                        notes=None,
                    )
                )

            cart.status = "CONVERTED"

            OrderService._create_audit_log(
                db,
                current_user=current_user,
                order=order,
                action="CREATE",
                description=(
                    f"Compra digital {order.order_code} creada "
                    f"desde el carrito {cart.id}."
                ),
            )

            db.commit()

        except Exception:
            db.rollback()
            raise

        created = OrderService._get_order(db, order.id)
        return OrderService._serialize(created)

    # =====================================================
    # CU34 - LISTAR / FILTRAR HISTORIAL
    # =====================================================

    @staticmethod
    def list_orders(
        db: Session,
        *,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        order_status: str | None = None,
        branch_id: int | None = None,
        customer_id: int | None = None,
        payment_status: str | None = None,
        payment_method: str | None = None,
        delivery_type: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
        min_total: Decimal | None = None,
        max_total: Decimal | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
    ) -> dict:
        page = max(1, page)
        page_size = max(1, min(page_size, 100))

        query = (
            OrderService._base_query(db)
            .join(User, Order.customer_id == User.id)
            .join(Branch, Order.branch_id == Branch.id)
        )

        role = OrderService._role_name(current_user)

        # Alcance por rol.
        if role == OrderService.CUSTOMER_ROLE:
            query = query.filter(Order.customer_id == current_user.id)

        elif role == OrderService.MANAGER_ROLE:
            manager_branch_id = OrderService._get_active_manager_branch(
                db,
                current_user,
            )

            if branch_id is not None and branch_id != manager_branch_id:
                raise PermissionError(
                    "No puedes consultar compras de otra sucursal."
                )

            query = query.filter(Order.branch_id == manager_branch_id)

        elif role == OrderService.ADMIN_ROLE:
            if branch_id is not None:
                query = query.filter(Order.branch_id == branch_id)

        else:
            raise PermissionError(
                "Tu rol no puede consultar compras digitales."
            )

        # El cliente nunca puede forzar otro customer_id.
        if role != OrderService.CUSTOMER_ROLE and customer_id is not None:
            query = query.filter(Order.customer_id == customer_id)

        if order_status:
            query = query.filter(Order.status == order_status)

        if delivery_type:
            query = query.filter(Order.delivery_type == delivery_type)

        if date_from is not None:
            query = query.filter(Order.created_at >= date_from)

        if date_to is not None:
            query = query.filter(Order.created_at <= date_to)

        if min_total is not None:
            query = query.filter(Order.total_amount >= min_total)

        if max_total is not None:
            query = query.filter(Order.total_amount <= max_total)

        if payment_status or payment_method:
            query = query.join(Payment, Payment.order_id == Order.id)

            if payment_status:
                query = query.filter(Payment.status == payment_status)

            if payment_method:
                query = query.filter(
                    Payment.payment_method == payment_method
                )

            query = query.distinct()

        if search:
            clean_search = search.strip()

            if clean_search:
                pattern = f"%{clean_search}%"
                conditions = [
                    Order.order_code.ilike(pattern),
                    User.first_name.ilike(pattern),
                    User.last_name.ilike(pattern),
                    User.email.ilike(pattern),
                    User.document_number.ilike(pattern),
                    Branch.name.ilike(pattern),
                    cast(Order.id, String).ilike(pattern),
                ]

                query = query.filter(or_(*conditions))

        total = query.order_by(None).count()
        total_pages = math.ceil(total / page_size) if total > 0 else 0

        sort_columns = {
            "created_at": Order.created_at,
            "updated_at": Order.updated_at,
            "total_amount": Order.total_amount,
            "order_code": Order.order_code,
            "status": Order.status,
        }

        sort_column = sort_columns.get(sort_by, Order.created_at)
        order_expression = (
            sort_column.asc()
            if sort_order == "asc"
            else sort_column.desc()
        )

        orders = (
            query.order_by(order_expression, Order.id.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
            .all()
        )

        return {
            "items": [OrderService._serialize(order) for order in orders],
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }

    # =====================================================
    # GESTIÓN OPERATIVA - RESUMEN PARA ADMIN / ENCARGADO
    # =====================================================

    @staticmethod
    def management_summary(
        db: Session,
        *,
        current_user: User,
        branch_id: int | None = None,
    ) -> dict:
        role = OrderService._role_name(current_user)

        if role not in {OrderService.ADMIN_ROLE, OrderService.MANAGER_ROLE}:
            raise PermissionError(
                "Tu rol no puede consultar el resumen operativo de pedidos."
            )

        effective_branch_id = branch_id
        branch_name = None

        if role == OrderService.MANAGER_ROLE:
            manager_branch_id = OrderService._get_active_manager_branch(
                db,
                current_user,
            )
            if branch_id is not None and branch_id != manager_branch_id:
                raise PermissionError(
                    "No puedes consultar pedidos de otra sucursal."
                )
            effective_branch_id = manager_branch_id

        query = db.query(Order)

        if effective_branch_id is not None:
            branch = (
                db.query(Branch)
                .filter(Branch.id == effective_branch_id)
                .first()
            )
            if branch is None:
                raise LookupError("La sucursal no existe.")
            branch_name = branch.name
            query = query.filter(Order.branch_id == effective_branch_id)

        rows = query.all()

        statuses = [
            "PENDING_PAYMENT",
            "PAYMENT_FAILED",
            "PAID",
            "PREPARING",
            "READY_FOR_PICKUP",
            "SHIPPED",
            "DELIVERED",
            "COMPLETED",
            "CANCELLED",
            "REFUNDED",
        ]

        counts = {status: 0 for status in statuses}
        total_revenue = Decimal("0.00")

        for order in rows:
            if order.status in counts:
                counts[order.status] += 1

            if order.status in {
                "PAID",
                "PREPARING",
                "READY_FOR_PICKUP",
                "SHIPPED",
                "DELIVERED",
                "COMPLETED",
            }:
                total_revenue += Decimal(order.total_amount or 0)

        attention_count = (
            counts["PAID"]
            + counts["PREPARING"]
            + counts["READY_FOR_PICKUP"]
            + counts["SHIPPED"]
            + counts["DELIVERED"]
        )

        return {
            "branch_id": effective_branch_id,
            "branch_name": branch_name,
            "total_orders": len(rows),
            "total_revenue": OrderService._money(total_revenue),
            "attention_count": attention_count,
            "pickup_ready_count": counts["READY_FOR_PICKUP"],
            "delivery_in_progress_count": (
                counts["SHIPPED"] + counts["DELIVERED"]
            ),
            "status_counts": [
                {"status": status, "count": counts[status]}
                for status in statuses
            ],
        }


    # =====================================================
    # CU34 - MI HISTORIAL (SOLO CLIENTE)
    # =====================================================

    @staticmethod
    def list_my_orders(
        db: Session,
        *,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        order_status: str | None = None,
        date_from: datetime | None = None,
        date_to: datetime | None = None,
    ) -> dict:
        if OrderService._role_name(current_user) != OrderService.CUSTOMER_ROLE:
            raise PermissionError(
                "La ruta /orders/mine está disponible solo para clientes."
            )

        return OrderService.list_orders(
            db=db,
            current_user=current_user,
            page=page,
            page_size=page_size,
            order_status=order_status,
            date_from=date_from,
            date_to=date_to,
        )


    # =====================================================
    # CU34 - CONSULTAR DETALLE
    # =====================================================

    @staticmethod
    def get_order(
        db: Session,
        *,
        current_user: User,
        order_id: int,
    ) -> dict:
        order = OrderService._get_order(db, order_id)

        OrderService._validate_order_access(
            db,
            order=order,
            current_user=current_user,
        )

        return OrderService._serialize(order)


    # =====================================================
    # CU33 - PREVISUALIZAR CHECKOUT (SIN CREAR COMPRA)
    # =====================================================

    @staticmethod
    def checkout_preview(
        db: Session,
        *,
        current_user: User,
        cart_id: int,
    ) -> dict:
        if OrderService._role_name(current_user) != OrderService.CUSTOMER_ROLE:
            raise PermissionError("Solo un cliente puede iniciar checkout.")

        cart = (
            db.query(ShoppingCart)
            .options(
                joinedload(ShoppingCart.branch),
                joinedload(ShoppingCart.items)
                .joinedload(CartItem.product_variant)
                .joinedload(ProductVariant.product),
                joinedload(ShoppingCart.items)
                .joinedload(CartItem.product_variant)
                .joinedload(ProductVariant.size),
                joinedload(ShoppingCart.items)
                .joinedload(CartItem.product_variant)
                .joinedload(ProductVariant.color),
            )
            .filter(ShoppingCart.id == cart_id)
            .first()
        )

        if cart is None:
            raise LookupError("El carrito no existe.")
        if cart.customer_id != current_user.id:
            raise PermissionError("No puedes consultar el carrito de otro cliente.")
        if cart.status != "ACTIVE":
            raise ValueError("El carrito no se encuentra activo.")
        if cart.branch_id is None or cart.branch is None:
            raise ValueError("Debes seleccionar una sucursal antes de pagar.")
        if not cart.items:
            raise ValueError("El carrito está vacío.")

        variant_ids = [item.product_variant_id for item in cart.items]
        inventories = (
            db.query(Inventory)
            .filter(
                Inventory.branch_id == cart.branch_id,
                Inventory.product_variant_id.in_(variant_ids),
                Inventory.is_active.is_(True),
            )
            .all()
        )
        inventory_by_variant = {i.product_variant_id: i for i in inventories}

        product_ids = list({
            item.product_variant.product_id
            for item in cart.items
            if item.product_variant is not None and item.product_variant.product is not None
        })
        promotions_by_product = CustomerPricingService.get_active_promotions_by_product(
            db, product_ids
        )

        items = []
        subtotal = Decimal("0.00")
        discounted_total = Decimal("0.00")
        total_units = 0

        for cart_item in sorted(cart.items, key=lambda item: item.id):
            variant = cart_item.product_variant
            if variant is None or not variant.is_active:
                raise ValueError("Una variante del carrito ya no está disponible.")
            if variant.product is None or not variant.product.is_active:
                raise ValueError("Un producto del carrito ya no está disponible.")

            inventory = inventory_by_variant.get(cart_item.product_variant_id)
            if inventory is None:
                raise ValueError(f"No existe inventario para {variant.sku} en la sucursal.")

            available = inventory.stock_quantity - inventory.reserved_quantity
            if available < cart_item.quantity:
                raise ValueError(
                    f"Stock insuficiente para {variant.product.name} ({variant.sku}). "
                    f"Disponible: {available}."
                )

            original_unit_price = OrderService._money(
                Decimal(variant.product.base_price or 0)
                + Decimal(variant.additional_price or 0)
            )
            applied_promotion = CustomerPricingService.choose_best_promotion(
                promotions_by_product.get(variant.product_id),
                original_unit_price,
            )
            unit_price = CustomerPricingService.apply_discount(
                original_unit_price,
                applied_promotion,
            )
            original_line_subtotal = OrderService._money(
                original_unit_price * cart_item.quantity
            )
            line_subtotal = OrderService._money(unit_price * cart_item.quantity)
            subtotal += original_line_subtotal
            discounted_total += line_subtotal
            total_units += cart_item.quantity
            items.append({
                "product_variant_id": variant.id,
                "sku": variant.sku,
                "product_name": variant.product.name,
                "size": variant.size.name,
                "color": variant.color.name,
                "quantity": cart_item.quantity,
                "original_unit_price": original_unit_price,
                "unit_price": unit_price,
                "discount_amount": OrderService._money(
                    (original_unit_price - unit_price) * cart_item.quantity
                ),
                "promotion": CustomerPricingService.promotion_payload(applied_promotion),
                "subtotal": line_subtotal,
            })

        subtotal = OrderService._money(subtotal)
        discounted_total = OrderService._money(discounted_total)
        discount_amount = OrderService._money(subtotal - discounted_total)
        total_amount = discounted_total

        return {
            "cart_id": cart.id,
            "branch_id": cart.branch_id,
            "branch_name": cart.branch.name,
            "items": items,
            "total_items": len(items),
            "total_units": total_units,
            "subtotal": subtotal,
            "discount_amount": discount_amount,
            "total_amount": total_amount,
            "currency": "BOB",
        }

    # =====================================================
    # CU33 - GESTIÓN OPERATIVA DE LA COMPRA
    # =====================================================

    @staticmethod
    def _release_reserved_inventory(
        db: Session,
        *,
        order: Order,
        user_id: int | None,
        reason: str,
    ) -> None:
        for item in order.items:
            inventory = (
                db.query(Inventory)
                .filter(
                    Inventory.branch_id == order.branch_id,
                    Inventory.product_variant_id == item.product_variant_id,
                )
                .with_for_update()
                .first()
            )
            if inventory is None:
                raise ValueError("No existe inventario para liberar la compra.")
            if inventory.reserved_quantity < item.quantity:
                raise ValueError("La reserva de inventario de la compra es inconsistente.")

            reserved_before = inventory.reserved_quantity
            reserved_after = reserved_before - item.quantity
            inventory.reserved_quantity = reserved_after

            db.add(InventoryMovement(
                inventory_id=inventory.id,
                movement_type="RELEASE",
                quantity=item.quantity,
                stock_before=inventory.stock_quantity,
                stock_after=inventory.stock_quantity,
                reserved_before=reserved_before,
                reserved_after=reserved_after,
                supplier_id=None,
                user_id=user_id,
                unit_cost=None,
                reference_type="ORDER",
                reference_id=order.id,
                reference_code=order.order_code,
                reason=reason,
                notes=None,
            ))

    @staticmethod
    def mark_paid_from_payment(
        db: Session,
        *,
        order: Order,
        payment: Payment,
    ) -> None:
        # Idempotencia: un webhook repetido no descuenta stock dos veces.
        if order.status in {
            "PAID", "PREPARING", "READY_FOR_PICKUP", "SHIPPED", "DELIVERED",
            "COMPLETED", "REFUNDED",
        }:
            return

        if order.status == "CANCELLED":
            raise ValueError("La compra está cancelada y no puede marcarse como pagada.")

        for item in order.items:
            inventory = (
                db.query(Inventory)
                .filter(
                    Inventory.branch_id == order.branch_id,
                    Inventory.product_variant_id == item.product_variant_id,
                )
                .with_for_update()
                .first()
            )
            if inventory is None:
                raise ValueError("No existe inventario para completar la compra.")
            if inventory.reserved_quantity < item.quantity:
                raise ValueError("La reserva de inventario de la compra es inconsistente.")
            if inventory.stock_quantity < item.quantity:
                raise ValueError("Stock físico insuficiente para completar la compra.")

            stock_before = inventory.stock_quantity
            reserved_before = inventory.reserved_quantity
            stock_after = stock_before - item.quantity
            reserved_after = reserved_before - item.quantity
            inventory.stock_quantity = stock_after
            inventory.reserved_quantity = reserved_after

            db.add(InventoryMovement(
                inventory_id=inventory.id,
                movement_type="SALE",
                quantity=item.quantity,
                stock_before=stock_before,
                stock_after=stock_after,
                reserved_before=reserved_before,
                reserved_after=reserved_after,
                supplier_id=None,
                user_id=payment.user_id,
                unit_cost=None,
                reference_type="ORDER",
                reference_id=order.id,
                reference_code=order.order_code,
                reason="Venta digital confirmada por pago electrónico.",
                notes=f"Pago {payment.payment_code}",
            ))

        order.status = "PAID"
        order.paid_at = datetime.now(timezone.utc)

        NotificationService.notify_order_status(
            db,
            order=order,
            status="PAID",
        )

    @staticmethod
    def update_order_status(
        db: Session,
        *,
        current_user: User,
        order_id: int,
        new_status: str,
        note: str | None = None,
        tracking_code: str | None = None,
    ) -> dict:
        role = OrderService._role_name(current_user)
        if role not in {OrderService.ADMIN_ROLE, OrderService.MANAGER_ROLE}:
            raise PermissionError("Solo administración o el encargado pueden gestionar compras.")

        # =================================================
        # BLOQUEO PESIMISTA DE LA ORDEN
        # =================================================
        #
        # No aplicamos with_for_update() sobre _base_query()
        # porque esa consulta usa varios joinedload() que
        # terminan generando LEFT OUTER JOIN.
        #
        # PostgreSQL no permite FOR UPDATE sobre el lado
        # nullable de un OUTER JOIN.
        #
        # Primero bloqueamos EXCLUSIVAMENTE la fila física de
        # la tabla orders. El bloqueo permanece activo durante
        # toda esta transacción hasta commit() o rollback().
        # =================================================

        locked_order_id = db.execute(
            select(Order.id)
            .where(Order.id == order_id)
            .with_for_update()
        ).scalar_one_or_none()

        if locked_order_id is None:
            raise LookupError("La compra digital no existe.")

        # La fila orders ya está bloqueada por esta transacción.
        # Ahora cargamos todas las relaciones necesarias SIN
        # volver a aplicar FOR UPDATE a los LEFT OUTER JOIN.
        order = (
            OrderService._base_query(db)
            .filter(Order.id == locked_order_id)
            .first()
        )

        if order is None:
            raise LookupError("La compra digital no existe.")

        OrderService._validate_order_access(
            db, order=order, current_user=current_user
        )

        allowed = set(OrderService._allowed_transitions(order))
        if new_status not in allowed:
            expected = ", ".join(sorted(allowed)) if allowed else "ninguno"
            raise ValueError(
                f"Transición inválida: {order.status} -> {new_status}. "
                f"Para este pedido ({order.delivery_type}) los siguientes estados "
                f"permitidos son: {expected}. "
                "Los estados de pago (PAID, PAYMENT_FAILED, REFUNDED) los gestiona "
                "el flujo de pagos y no el encargado."
            )

        if new_status == "READY_FOR_PICKUP" and order.delivery_type != "PICKUP":
            raise ValueError(
                "READY_FOR_PICKUP solo aplica a pedidos con recojo en sucursal."
            )

        if new_status in {"SHIPPED", "DELIVERED"} and order.delivery_type != "DELIVERY":
            raise ValueError(
                f"{new_status} solo aplica a pedidos con envío a domicilio."
            )

        old_status = order.status
        if new_status == "CANCELLED":
            OrderService._release_reserved_inventory(
                db,
                order=order,
                user_id=current_user.id,
                reason="Reserva liberada por cancelación de compra digital.",
            )

        now = datetime.now(timezone.utc)
        if new_status == "READY_FOR_PICKUP":
            order.ready_for_pickup_at = now
            order.tracking_code = None
        elif new_status == "SHIPPED":
            order.shipped_at = now
            clean_tracking = (tracking_code or "").strip() or None
            order.tracking_code = clean_tracking
        elif new_status == "DELIVERED":
            order.delivered_at = now
        elif new_status == "COMPLETED":
            order.completed_at = now
        elif new_status == "CANCELLED":
            order.cancelled_at = now

        order.status = new_status

        NotificationService.notify_order_status(
            db,
            order=order,
            status=new_status,
            reason=note.strip() if note and note.strip() else None,
        )

        OrderService._create_audit_log(
            db,
            current_user=current_user,
            order=order,
            action="UPDATE_STATUS",
            description=(
                f"Compra {order.order_code}: {old_status} -> {new_status}."
                + (f" Nota: {note.strip()}" if note and note.strip() else "")
            ),
        )

        try:
            db.commit()
        except Exception:
            db.rollback()
            raise

        updated = OrderService._get_order(db, order.id)
        return OrderService._serialize(updated)
