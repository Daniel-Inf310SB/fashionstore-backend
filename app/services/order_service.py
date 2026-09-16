from __future__ import annotations

import math

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import String, cast, or_
from sqlalchemy.orm import Session, joinedload

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
            "created_at": order.created_at,
            "updated_at": order.updated_at,
            "total_items": len(sorted_items),
            "total_units": total_units,
            "customer": order.customer,
            "branch": order.branch,
            "items": sorted_items,
            "payments": sorted_payments,
            "receipt": order.receipt,
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

        subtotal = Decimal("0.00")
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

            unit_price = OrderService._money(
                Decimal(variant.product.base_price or 0)
                + Decimal(variant.additional_price or 0)
            )
            item_subtotal = OrderService._money(
                unit_price * cart_item.quantity
            )
            subtotal += item_subtotal
            prepared_items.append(
                (cart_item, unit_price, item_subtotal)
            )

        subtotal = OrderService._money(subtotal)

        # Las promociones todavía no se aplican en CU32; por consistencia,
        # CU33 conserva discount_amount en 0 hasta integrar esa regla.
        discount_amount = Decimal("0.00")
        total_amount = OrderService._money(
            subtotal - discount_amount
        )

        try:
            order = Order(
                order_code=OrderService._generate_order_code(),
                customer_id=current_user.id,
                branch_id=cart.branch_id,
                status="PENDING_PAYMENT",
                subtotal=subtotal,
                discount_amount=discount_amount,
                total_amount=total_amount,
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
