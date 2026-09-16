from __future__ import annotations

import math

from datetime import datetime, timezone
from decimal import Decimal
from uuid import uuid4

from sqlalchemy import (
    String,
    and_,
    cast,
    or_,
)

from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.audit_log import AuditLog
from app.models.branch import Branch
from app.models.employee_branch import EmployeeBranch
from app.models.inventory import Inventory
from app.models.payment import Payment
from app.models.product_variant import ProductVariant
from app.models.product import Product
from app.models.role import Role
from app.models.sale import Sale
from app.models.sale_item import SaleItem
from app.models.user import User

from app.schemas.sale import SaleCreate


class SaleService:

    ADMIN_ROLE = "ADMINISTRADOR"
    MANAGER_ROLE = "ENCARGADO_SUCURSAL"
    CASHIER_ROLE = "CAJERO"


    # =====================================================
    # HELPERS
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


    @staticmethod
    def _role(
        user,
    ):

        return (
            user.role.name
            if user.role
            else None
        )


    @staticmethod
    def _active_branch(
        db,
        user,
    ):

        assignment = (
            db.query(
                EmployeeBranch
            )
            .filter(
                EmployeeBranch.user_id
                == user.id,

                EmployeeBranch.is_active.is_(
                    True
                ),
            )
            .first()
        )

        if assignment is None:

            raise PermissionError(
                "El empleado no tiene una sucursal activa asignada."
            )

        return assignment.branch_id


    @staticmethod
    def _base(
        db,
    ):

        return (
            db.query(
                Sale
            )
            .options(
                joinedload(
                    Sale.branch
                ),

                joinedload(
                    Sale.cashier
                ),

                joinedload(
                    Sale.customer
                ),

                joinedload(
                    Sale.items
                )
                .joinedload(
                    SaleItem.product_variant
                )
                .joinedload(
                    ProductVariant.product
                ),

                joinedload(
                    Sale.items
                )
                .joinedload(
                    SaleItem.product_variant
                )
                .joinedload(
                    ProductVariant.size
                ),

                joinedload(
                    Sale.items
                )
                .joinedload(
                    SaleItem.product_variant
                )
                .joinedload(
                    ProductVariant.color
                ),

                joinedload(
                    Sale.payments
                ),

                joinedload(
                    Sale.receipt
                ),
            )
        )


    @staticmethod
    def _get(
        db,
        sale_id,
    ):

        sale = (
            SaleService
            ._base(
                db
            )
            .filter(
                Sale.id
                == sale_id
            )
            .first()
        )

        if sale is None:

            raise LookupError(
                "La venta presencial no existe."
            )

        return sale


    @staticmethod
    def _check_access(
        db,
        sale,
        current_user,
    ):

        role = (
            SaleService._role(
                current_user
            )
        )

        if (
            role
            == SaleService.ADMIN_ROLE
        ):

            return


        if (
            role
            == SaleService.MANAGER_ROLE
        ):

            if (
                sale.branch_id
                != SaleService._active_branch(
                    db,
                    current_user,
                )
            ):

                raise PermissionError(
                    "No puedes consultar ventas de otra sucursal."
                )

            return


        if (
            role
            == SaleService.CASHIER_ROLE
        ):

            if (
                sale.cashier_id
                != current_user.id
            ):

                raise PermissionError(
                    "No puedes consultar ventas de otro cajero."
                )

            return


        raise PermissionError(
            "Tu rol no puede consultar ventas presenciales."
        )


    @staticmethod
    def _serialize(
        sale,
    ):

        items = sorted(
            sale.items,
            key=lambda item: item.id,
        )

        payments = sorted(
            sale.payments,
            key=lambda payment: payment.id,
        )

        return {
            "id":
                sale.id,

            "sale_code":
                sale.sale_code,

            "branch_id":
                sale.branch_id,

            "cashier_id":
                sale.cashier_id,

            "customer_id":
                sale.customer_id,

            "status":
                sale.status,

            "subtotal":
                SaleService._money(
                    sale.subtotal
                ),

            "discount_amount":
                SaleService._money(
                    sale.discount_amount
                ),

            "total_amount":
                SaleService._money(
                    sale.total_amount
                ),

            "created_at":
                sale.created_at,

            "updated_at":
                sale.updated_at,

            "total_items":
                len(
                    items
                ),

            "total_units":
                sum(
                    item.quantity
                    for item in items
                ),

            "branch":
                sale.branch,

            "cashier":
                sale.cashier,

            "customer":
                sale.customer,

            "items":
                items,

            "payments":
                payments,

            "receipt":
                sale.receipt,
        }


    # =====================================================
    # CONTEXTO CAJERO
    # =====================================================

    @staticmethod
    def get_cashier_context(
        db: Session,
        *,
        current_user: User,
    ):

        if (
            SaleService._role(
                current_user
            )
            != SaleService.CASHIER_ROLE
        ):

            raise PermissionError(
                "Solo un cajero puede acceder al punto de venta."
            )


        branch_id = (
            SaleService._active_branch(
                db,
                current_user,
            )
        )


        branch = (
            db.query(
                Branch
            )
            .filter(
                Branch.id
                == branch_id,

                Branch.is_active.is_(
                    True
                ),
            )
            .first()
        )


        if branch is None:

            raise LookupError(
                "La sucursal asignada no existe o está inactiva."
            )


        return {
            "cashier":
                current_user,

            "branch":
                branch,
        }


    # =====================================================
    # CATÁLOGO POS
    # =====================================================

    @staticmethod
    def get_pos_catalog(
        db: Session,
        *,
        current_user: User,
        page=1,
        page_size=24,
        search=None,
    ):

        if (
            SaleService._role(
                current_user
            )
            != SaleService.CASHIER_ROLE
        ):

            raise PermissionError(
                "Solo un cajero puede consultar el catálogo del punto de venta."
            )


        branch_id = (
            SaleService._active_branch(
                db,
                current_user,
            )
        )


        query = (
            db.query(
                Inventory
            )
            .join(
                ProductVariant,
                Inventory.product_variant_id
                == ProductVariant.id,
            )
            .join(
                Product,
                ProductVariant.product_id
                == Product.id,
            )
            .options(
                joinedload(
                    Inventory.product_variant
                )
                .joinedload(
                    ProductVariant.product
                ),

                joinedload(
                    Inventory.product_variant
                )
                .joinedload(
                    ProductVariant.size
                ),

                joinedload(
                    Inventory.product_variant
                )
                .joinedload(
                    ProductVariant.color
                ),
            )
            .filter(
                Inventory.branch_id
                == branch_id,

                Inventory.is_active.is_(
                    True
                ),

                ProductVariant.is_active.is_(
                    True
                ),

                Product.is_active.is_(
                    True
                ),

                (
                    Inventory.stock_quantity
                    - Inventory.reserved_quantity
                )
                > 0,
            )
        )


        if (
            search
            and search.strip()
        ):

            term = (
                f"%{search.strip()}%"
            )

            query = (
                query.filter(
                    or_(
                        Product.code.ilike(
                            term
                        ),

                        Product.name.ilike(
                            term
                        ),

                        Product.brand.ilike(
                            term
                        ),

                        ProductVariant.sku.ilike(
                            term
                        ),
                    )
                )
            )


        total = (
            query.count()
        )


        rows = (
            query
            .order_by(
                Product.name.asc(),
                ProductVariant.sku.asc(),
            )
            .offset(
                (page - 1)
                * page_size
            )
            .limit(
                page_size
            )
            .all()
        )


        items = []


        for inventory in rows:

            variant = (
                inventory.product_variant
            )

            product = (
                variant.product
            )

            unit_price = (
                SaleService._money(
                    Decimal(
                        product.base_price
                        or 0
                    )
                    +
                    Decimal(
                        variant.additional_price
                        or 0
                    )
                )
            )


            items.append(
                {
                    "inventory_id":
                        inventory.id,

                    "product_variant_id":
                        variant.id,

                    "product_id":
                        product.id,

                    "product_code":
                        product.code,

                    "product_name":
                        product.name,

                    "brand":
                        product.brand,

                    "sku":
                        variant.sku,

                    "size_name":
                        variant.size.name,

                    "color_name":
                        variant.color.name,

                    "color_hex_code":
                        variant.color.hex_code,

                    "image_url":
                        variant.image_url
                        or product.cover_image_url,

                    "available_quantity":
                        inventory.available_quantity,

                    "unit_price":
                        unit_price,
                }
            )


        return {
            "items":
                items,

            "page":
                page,

            "page_size":
                page_size,

            "total":
                total,

            "total_pages":
                (
                    math.ceil(
                        total
                        / page_size
                    )
                    if total
                    else 0
                ),
        }


    # =====================================================
    # BUSCAR CLIENTES POS
    # =====================================================

    @staticmethod
    def search_customers(
        db: Session,
        *,
        current_user: User,
        page=1,
        page_size=10,
        search=None,
    ):

        if (
            SaleService._role(
                current_user
            )
            != SaleService.CASHIER_ROLE
        ):

            raise PermissionError(
                "Solo un cajero puede buscar clientes desde el punto de venta."
            )


        query = (
            db.query(
                User
            )
            .join(
                Role,
                User.role_id
                == Role.id,
            )
            .filter(
                Role.name
                == "CLIENTE",

                User.is_active.is_(
                    True
                ),
            )
        )


        if (
            search
            and search.strip()
        ):

            term = (
                f"%{search.strip()}%"
            )

            query = (
                query.filter(
                    or_(
                        User.first_name.ilike(
                            term
                        ),

                        User.last_name.ilike(
                            term
                        ),

                        User.email.ilike(
                            term
                        ),

                        User.document_number.ilike(
                            term
                        ),

                        User.phone.ilike(
                            term
                        ),
                    )
                )
            )


        total = (
            query.count()
        )


        rows = (
            query
            .order_by(
                User.first_name.asc(),
                User.last_name.asc(),
            )
            .offset(
                (page - 1)
                * page_size
            )
            .limit(
                page_size
            )
            .all()
        )


        return {
            "items":
                rows,

            "page":
                page,

            "page_size":
                page_size,

            "total":
                total,

            "total_pages":
                (
                    math.ceil(
                        total
                        / page_size
                    )
                    if total
                    else 0
                ),
        }


    # =====================================================
    # CREAR VENTA
    # CU35
    # =====================================================

    @staticmethod
    def create_sale(
        db: Session,
        *,
        current_user: User,
        data: SaleCreate,
    ):

        if (
            SaleService._role(
                current_user
            )
            != SaleService.CASHIER_ROLE
        ):

            raise PermissionError(
                "Solo un cajero puede registrar una venta presencial."
            )


        branch_id = (
            SaleService._active_branch(
                db,
                current_user,
            )
        )


        if (
            data.branch_id
            is not None
            and data.branch_id
            != branch_id
        ):

            raise PermissionError(
                "No puedes vender desde una sucursal distinta a la asignada."
            )


        branch = (
            db.query(
                Branch
            )
            .filter(
                Branch.id
                == branch_id,

                Branch.is_active.is_(
                    True
                ),
            )
            .first()
        )


        if branch is None:

            raise ValueError(
                "La sucursal asignada no existe o está inactiva."
            )


        if (
            data.customer_id
            is not None
        ):

            customer = (
                db.query(
                    User
                )
                .filter(
                    User.id
                    == data.customer_id,

                    User.is_active.is_(
                        True
                    ),
                )
                .first()
            )


            if customer is None:

                raise LookupError(
                    "El cliente indicado no existe o está inactivo."
                )


        quantities = {}


        for item in data.items:

            quantities[
                item.product_variant_id
            ] = (
                quantities.get(
                    item.product_variant_id,
                    0,
                )
                + item.quantity
            )


        variant_ids = (
            list(
                quantities
            )
        )


        variants = (
            db.query(
                ProductVariant
            )
            .options(
                joinedload(
                    ProductVariant.product
                )
            )
            .filter(
                ProductVariant.id.in_(
                    variant_ids
                )
            )
            .all()
        )


        variant_map = {
            variant.id:
                variant

            for variant
            in variants
        }


        inventories = (
            db.query(
                Inventory
            )
            .filter(
                Inventory.branch_id
                == branch_id,

                Inventory.product_variant_id.in_(
                    variant_ids
                ),

                Inventory.is_active.is_(
                    True
                ),
            )
            .all()
        )


        inventory_map = {
            inventory.product_variant_id:
                inventory

            for inventory
            in inventories
        }


        prepared = []

        subtotal = Decimal(
            "0.00"
        )


        for (
            variant_id,
            quantity,
        ) in quantities.items():

            variant = (
                variant_map.get(
                    variant_id
                )
            )


            if (
                variant is None
                or not variant.is_active
                or variant.product is None
                or not variant.product.is_active
            ):

                raise ValueError(
                    f"La variante {variant_id} no está disponible."
                )


            inventory = (
                inventory_map.get(
                    variant_id
                )
            )


            if inventory is None:

                raise ValueError(
                    f"No existe inventario para {variant.sku} en esta sucursal."
                )


            if (
                inventory.available_quantity
                < quantity
            ):

                raise ValueError(
                    f"Stock insuficiente para {variant.sku}. "
                    f"Disponible: {inventory.available_quantity}."
                )


            price = (
                SaleService._money(
                    Decimal(
                        variant.product.base_price
                        or 0
                    )
                    +
                    Decimal(
                        variant.additional_price
                        or 0
                    )
                )
            )


            line_total = (
                SaleService._money(
                    price
                    * quantity
                )
            )


            subtotal += (
                line_total
            )


            prepared.append(
                (
                    variant,
                    quantity,
                    price,
                    line_total,
                )
            )


        subtotal = (
            SaleService._money(
                subtotal
            )
        )


        sale = Sale(
            sale_code=(
                f"SALE-"
                f"{datetime.now(timezone.utc).strftime('%Y%m%d')}-"
                f"{uuid4().hex[:10].upper()}"
            ),

            branch_id=
                branch_id,

            cashier_id=
                current_user.id,

            customer_id=
                data.customer_id,

            status=
                "PENDING",

            subtotal=
                subtotal,

            discount_amount=
                Decimal("0.00"),

            total_amount=
                subtotal,
        )


        db.add(
            sale
        )

        db.flush()


        for (
            variant,
            quantity,
            price,
            line_total,
        ) in prepared:

            db.add(
                SaleItem(
                    sale_id=
                        sale.id,

                    product_variant_id=
                        variant.id,

                    quantity=
                        quantity,

                    unit_price=
                        price,

                    subtotal=
                        line_total,
                )
            )


        db.add(
            AuditLog(
                user_id=
                    current_user.id,

                action=
                    "CREATE",

                module=
                    "SALES",

                entity_type=
                    "Sale",

                entity_id=
                    sale.id,

                description=(
                    f"Venta presencial {sale.sale_code} creada."
                ),

                old_values=
                    None,

                new_values={
                    "status":
                        "PENDING",

                    "branch_id":
                        branch_id,

                    "total_amount":
                        str(
                            sale.total_amount
                        ),
                },

                status=
                    "SUCCESS",
            )
        )


        db.commit()


        return (
            SaleService._serialize(
                SaleService._get(
                    db,
                    sale.id,
                )
            )
        )


    # =====================================================
    # OBTENER VENTA
    # =====================================================

    @staticmethod
    def get_sale(
        db,
        *,
        current_user,
        sale_id,
    ):

        sale = (
            SaleService._get(
                db,
                sale_id,
            )
        )

        SaleService._check_access(
            db,
            sale,
            current_user,
        )

        return (
            SaleService._serialize(
                sale
            )
        )


    # =====================================================
    # LISTAR / FILTRAR VENTAS
    # ADMIN: TODAS
    # ENCARGADO: SU SUCURSAL
    # CAJERO: SOLO SUS VENTAS
    # =====================================================

    @staticmethod
    def list_sales(
        db,
        *,
        current_user,
        page=1,
        page_size=10,
        search=None,
        branch_id=None,
        cashier_id=None,
        customer_id=None,
        customer_search=None,
        cashier_search=None,
        payment_method=None,
        sale_status=None,
        date_from=None,
        date_to=None,
    ):

        query = (
            SaleService._base(
                db
            )
        )


        role = (
            SaleService._role(
                current_user
            )
        )


        # =================================================
        # SEGURIDAD POR ROL
        # =================================================

        if (
            role
            == SaleService.MANAGER_ROLE
        ):

            manager_branch_id = (
                SaleService._active_branch(
                    db,
                    current_user,
                )
            )

            if (
                branch_id is not None
                and branch_id != manager_branch_id
            ):
                raise PermissionError(
                    "No puedes consultar ventas de otra sucursal."
                )

            query = (
                query.filter(
                    Sale.branch_id
                    == manager_branch_id
                )
            )


        elif (
            role
            == SaleService.CASHIER_ROLE
        ):

            query = (
                query.filter(
                    Sale.cashier_id
                    == current_user.id
                )
            )


        elif (
            role
            != SaleService.ADMIN_ROLE
        ):

            raise PermissionError(
                "Tu rol no puede consultar ventas presenciales."
            )


        # =================================================
        # BÚSQUEDA GENERAL
        # =================================================

        if (
            search
            and search.strip()
        ):

            term = (
                f"%{search.strip()}%"
            )

            query = (
                query.filter(
                    or_(
                        Sale.sale_code.ilike(
                            term
                        ),

                        cast(
                            Sale.id,
                            String,
                        ).ilike(
                            term
                        ),
                    )
                )
            )


        # =================================================
        # SUCURSAL
        # =================================================

        if (
            branch_id
            is not None
        ):

            query = (
                query.filter(
                    Sale.branch_id
                    == branch_id
                )
            )


        # =================================================
        # CAJERO ID
        # =================================================

        if (
            cashier_id
            is not None
        ):

            query = (
                query.filter(
                    Sale.cashier_id
                    == cashier_id
                )
            )


        # =================================================
        # CLIENTE ID
        # =================================================

        if (
            customer_id
            is not None
        ):

            query = (
                query.filter(
                    Sale.customer_id
                    == customer_id
                )
            )


        # =================================================
        # CLIENTE
        # Nombre, apellido, correo o documento
        # =================================================

        if (
            customer_search
            and customer_search.strip()
        ):

            customer_term = (
                f"%{customer_search.strip()}%"
            )

            query = (
                query.filter(
                    Sale.customer.has(
                        or_(
                            User.first_name.ilike(
                                customer_term
                            ),

                            User.last_name.ilike(
                                customer_term
                            ),

                            User.email.ilike(
                                customer_term
                            ),

                            User.document_number.ilike(
                                customer_term
                            ),
                        )
                    )
                )
            )


        # =================================================
        # CAJERO
        # Nombre, apellido o correo
        # =================================================

        if (
            cashier_search
            and cashier_search.strip()
        ):

            cashier_term = (
                f"%{cashier_search.strip()}%"
            )

            query = (
                query.filter(
                    Sale.cashier.has(
                        or_(
                            User.first_name.ilike(
                                cashier_term
                            ),

                            User.last_name.ilike(
                                cashier_term
                            ),

                            User.email.ilike(
                                cashier_term
                            ),
                        )
                    )
                )
            )


        # =================================================
        # MÉTODO DE PAGO
        # Solo considera pagos aprobados
        # =================================================

        if (
            payment_method
            is not None
        ):

            query = (
                query.filter(
                    Sale.payments.any(
                        and_(
                            Payment.payment_method
                            == payment_method,

                            Payment.status
                            == "APPROVED",
                        )
                    )
                )
            )


        # =================================================
        # ESTADO
        # =================================================

        if (
            sale_status
            is not None
        ):

            query = (
                query.filter(
                    Sale.status
                    == sale_status
                )
            )


        # =================================================
        # FECHAS
        # =================================================

        if (
            date_from
            is not None
        ):

            query = (
                query.filter(
                    Sale.created_at
                    >= date_from
                )
            )


        if (
            date_to
            is not None
        ):

            query = (
                query.filter(
                    Sale.created_at
                    <= date_to
                )
            )


        # =================================================
        # PAGINACIÓN
        # =================================================

        total = (
            query.count()
        )


        rows = (
            query
            .order_by(
                Sale.created_at.desc()
            )
            .offset(
                (page - 1)
                * page_size
            )
            .limit(
                page_size
            )
            .all()
        )


        return {
            "items": [
                SaleService._serialize(
                    sale
                )
                for sale in rows
            ],

            "page":
                page,

            "page_size":
                page_size,

            "total":
                total,

            "total_pages":
                (
                    math.ceil(
                        total
                        / page_size
                    )
                    if total
                    else 0
                ),
        }


    # =====================================================
    # CANCELAR VENTA
    # =====================================================

    @staticmethod
    def cancel_sale(
        db,
        *,
        current_user,
        sale_id,
    ):

        sale = (
            SaleService._get(
                db,
                sale_id,
            )
        )


        role = (
            SaleService._role(
                current_user
            )
        )


        if (
            role
            == SaleService.CASHIER_ROLE
        ):

            if (
                sale.cashier_id
                != current_user.id
            ):
                raise PermissionError(
                    "Solo puedes cancelar tus propias ventas pendientes."
                )


        elif (
            role
            == SaleService.MANAGER_ROLE
        ):

            manager_branch_id = (
                SaleService._active_branch(
                    db,
                    current_user,
                )
            )

            if (
                sale.branch_id
                != manager_branch_id
            ):
                raise PermissionError(
                    "No puedes cancelar ventas de otra sucursal."
                )


        elif (
            role
            != SaleService.ADMIN_ROLE
        ):

            raise PermissionError(
                "Tu rol no puede cancelar ventas presenciales."
            )


        if (
            sale.status
            != "PENDING"
        ):

            raise ValueError(
                "Solo se puede cancelar una venta pendiente."
            )


        sale.status = (
            "CANCELLED"
        )


        db.add(
            AuditLog(
                user_id=
                    current_user.id,

                action=
                    "CANCEL",

                module=
                    "SALES",

                entity_type=
                    "Sale",

                entity_id=
                    sale.id,

                description=(
                    f"Venta {sale.sale_code} cancelada."
                ),

                old_values={
                    "status":
                        "PENDING",
                },

                new_values={
                    "status":
                        "CANCELLED",
                },

                status=
                    "SUCCESS",
            )
        )


        db.commit()


        return (
            SaleService._serialize(
                SaleService._get(
                    db,
                    sale.id,
                )
            )
        )
