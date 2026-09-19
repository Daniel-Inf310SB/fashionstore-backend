from __future__ import annotations

import logging
import math

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from decimal import Decimal

from uuid import uuid4

from sqlalchemy import (
    func,
    or_,
)

from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.core.config import settings
from app.models.audit_log import AuditLog

from app.models.branch import Branch

from app.models.color import Color

from app.models.inventory import Inventory

from app.models.inventory_movement import (
    InventoryMovement,
)

from app.models.employee_branch import (
    EmployeeBranch,
)

from app.models.product import Product

from app.models.product_variant import (
    ProductVariant,
)

from app.models.reservation import Reservation

from app.models.reservation_item import (
    ReservationItem,
)

from app.models.size import Size

from app.models.user import User

from app.schemas.reservation import (
    ReservationAddItems,
    ReservationCreate,
)

from app.services.email_service import EmailService
from app.services.notification_service import NotificationService


logger = logging.getLogger(__name__)


class ReservationService:

    # =====================================================
    # CONSTANTES
    # =====================================================

    ADMIN_ROLES = {
        "ADMINISTRADOR",
        "SUPERADMIN",
    }

    MANAGER_ROLE = "ENCARGADO_SUCURSAL"

    CUSTOMER_ROLE = "CLIENTE"

    CANCELLABLE_STATUSES = {
        "PENDING",
        "CONFIRMED",
    }

    # Para el cliente, una reserva sigue activa hasta que
    # finaliza, se cancela o vence.
    ACTIVE_CUSTOMER_STATUSES = {
        "PENDING",
        "CONFIRMED",
        "PREPARING",
        "READY",
        "ATTENDED",
    }

    ACTIVE_ITEM_STATUSES = {
        "PENDING",
        "RESERVED",
    }

    # El plazo de retiro empieza cuando la sucursal CONFIRMA
    # la reserva. Una solicitud PENDING todavía no tiene expires_at.
    EXPIRABLE_STATUSES = {
        "CONFIRMED",
        "PREPARING",
        "READY",
    }


    # =====================================================
    # ROL DEL USUARIO
    # =====================================================

    @staticmethod
    def _role_name(
        user: User,
    ) -> str:

        if user.role is None:
            return ""

        return (
            user.role.name
            .strip()
            .upper()
        )


    @staticmethod
    def _is_customer(
        user: User,
    ) -> bool:

        return (
            ReservationService
            ._role_name(
                user
            )
            ==
            ReservationService.CUSTOMER_ROLE
        )


    # =====================================================
    # SUCURSAL ACTIVA DEL ENCARGADO
    # =====================================================

    @staticmethod
    def _get_manager_branch_id(
        db: Session,

        current_user: User,
    ) -> int:

        assignment = (
            db.query(
                EmployeeBranch
            )
            .join(
                Branch,

                EmployeeBranch.branch_id
                ==
                Branch.id,
            )
            .filter(
                EmployeeBranch.user_id
                ==
                current_user.id,

                EmployeeBranch.is_active.is_(
                    True
                ),

                Branch.is_active.is_(
                    True
                ),
            )
            .first()
        )

        if assignment is None:
            raise PermissionError(
                "El encargado no tiene una "
                "sucursal activa asignada."
            )

        return assignment.branch_id


    # =====================================================
    # RESOLVER ALCANCE DE SUCURSAL PARA LISTADOS
    # =====================================================

    @staticmethod
    def _resolve_list_branch_scope(
        db: Session,

        current_user: User,

        requested_branch_id: int | None = None,
    ) -> int | None:

        role = (
            ReservationService
            ._role_name(
                current_user
            )
        )

        if role in ReservationService.ADMIN_ROLES:
            return requested_branch_id

        if role == ReservationService.MANAGER_ROLE:

            manager_branch_id = (
                ReservationService
                ._get_manager_branch_id(
                    db,
                    current_user,
                )
            )

            if (
                requested_branch_id is not None
                and
                requested_branch_id
                !=
                manager_branch_id
            ):
                raise PermissionError(
                    "No puedes consultar reservas "
                    "de otra sucursal."
                )

            return manager_branch_id

        if role == ReservationService.CUSTOMER_ROLE:
            return requested_branch_id

        raise PermissionError(
            "Tu rol no puede consultar reservas."
        )


    # =====================================================
    # QUERY BASE
    # =====================================================

    @staticmethod
    def _base_query(
        db: Session,
    ):

        return (
            db.query(
                Reservation
            )
            .options(
                joinedload(
                    Reservation.customer
                ),

                joinedload(
                    Reservation.branch
                ),

                joinedload(
                    Reservation.items
                )
                .joinedload(
                    ReservationItem.product_variant
                )
                .joinedload(
                    ProductVariant.product
                ),

                joinedload(
                    Reservation.items
                )
                .joinedload(
                    ReservationItem.product_variant
                )
                .joinedload(
                    ProductVariant.size
                ),

                joinedload(
                    Reservation.items
                )
                .joinedload(
                    ReservationItem.product_variant
                )
                .joinedload(
                    ProductVariant.color
                ),
            )
        )


    # =====================================================
    # OBTENER RESERVA
    # =====================================================

    @staticmethod
    def _get_reservation(
        db: Session,

        reservation_id: int,
    ) -> Reservation:

        reservation = (
            ReservationService
            ._base_query(
                db
            )
            .filter(
                Reservation.id
                ==
                reservation_id
            )
            .first()
        )


        if reservation is None:

            raise LookupError(
                "La reserva no existe."
            )


        return reservation


    # =====================================================
    # VALIDAR ACCESO
    # =====================================================

    @staticmethod
    def _validate_reservation_access(
        db: Session,

        reservation: Reservation,

        current_user: User,
    ) -> None:

        role = (
            ReservationService
            ._role_name(
                current_user
            )
        )

        if role in ReservationService.ADMIN_ROLES:
            return

        if role == ReservationService.CUSTOMER_ROLE:

            if (
                reservation.customer_id
                !=
                current_user.id
            ):
                raise PermissionError(
                    "No puedes acceder a "
                    "la reserva de otro cliente."
                )

            return

        if role == ReservationService.MANAGER_ROLE:

            manager_branch_id = (
                ReservationService
                ._get_manager_branch_id(
                    db,
                    current_user,
                )
            )

            if (
                reservation.branch_id
                !=
                manager_branch_id
            ):
                raise PermissionError(
                    "No puedes acceder a reservas "
                    "de otra sucursal."
                )

            return

        raise PermissionError(
            "Tu rol no puede acceder a reservas."
        )


    # =====================================================
    # VALIDAR GESTIÓN OPERATIVA
    # =====================================================

    @staticmethod
    def _validate_staff_management_access(
        db: Session,

        reservation: Reservation,

        current_user: User,
    ) -> None:

        role = (
            ReservationService
            ._role_name(
                current_user
            )
        )

        if role in ReservationService.ADMIN_ROLES:
            return

        if role == ReservationService.MANAGER_ROLE:

            manager_branch_id = (
                ReservationService
                ._get_manager_branch_id(
                    db,
                    current_user,
                )
            )

            if (
                reservation.branch_id
                !=
                manager_branch_id
            ):
                raise PermissionError(
                    "No puedes gestionar reservas "
                    "de otra sucursal."
                )

            return

        raise PermissionError(
            "La gestión operativa de reservas "
            "corresponde al administrador o al "
            "encargado de la sucursal."
        )


    # =====================================================
    # GENERAR CÓDIGO
    # =====================================================

    @staticmethod
    def _generate_code() -> str:

        date_part = (
            datetime.now(
                timezone.utc
            )
            .strftime(
                "%Y%m%d"
            )
        )


        random_part = (
            uuid4()
            .hex[:10]
            .upper()
        )


        return (
            f"RSV-"
            f"{date_part}-"
            f"{random_part}"
        )


    # =====================================================
    # MOVIMIENTO DE INVENTARIO
    # =====================================================

    @staticmethod
    def _create_inventory_movement(
        db: Session,

        *,
        inventory: Inventory,

        reservation: Reservation,

        movement_type: str,

        quantity: int,

        reserved_before: int,

        reserved_after: int,

        user_id: int | None,

        reason: str,
    ) -> None:

        movement = InventoryMovement(
            inventory_id=
                inventory.id,

            movement_type=
                movement_type,

            quantity=
                quantity,

            stock_before=
                inventory.stock_quantity,

            stock_after=
                inventory.stock_quantity,

            reserved_before=
                reserved_before,

            reserved_after=
                reserved_after,

            supplier_id=
                None,

            user_id=
                user_id,

            unit_cost=
                None,

            reference_type=
                "RESERVATION",

            reference_id=
                reservation.id,

            reference_code=
                reservation.reservation_code,

            reason=
                reason,

            notes=
                None,
        )


        db.add(
            movement
        )


    # =====================================================
    # AUDITORÍA
    # =====================================================

    @staticmethod
    def _create_audit_log(
        db: Session,

        *,
        user_id: int | None,

        action: str,

        reservation: Reservation,

        description: str,

        old_values: dict | None = None,

        new_values: dict | None = None,
    ) -> None:

        audit = AuditLog(
            user_id=
                user_id,

            action=
                action,

            module=
                "RESERVATIONS",

            entity_type=
                "Reservation",

            entity_id=
                reservation.id,

            description=
                description,

            old_values=
                old_values,

            new_values=
                new_values,

            status=
                "SUCCESS",
        )


        db.add(
            audit
        )


    # =====================================================
    # SERIALIZAR
    # =====================================================

    @staticmethod
    def _serialize(
        reservation: Reservation,
    ) -> dict:

        items = []

        total_units = 0

        total_amount = Decimal(
            "0.00"
        )


        sorted_items = sorted(
            reservation.items,

            key=lambda item:
                item.id,
        )


        for item in sorted_items:

            subtotal = (
                Decimal(
                    item.unit_price
                )
                *
                item.quantity
            ).quantize(
                Decimal(
                    "0.01"
                )
            )


            total_units += (
                item.quantity
            )


            total_amount += (
                subtotal
            )


            items.append(
                {
                    "id":
                        item.id,

                    "reservation_id":
                        item.reservation_id,

                    "product_variant_id":
                        item.product_variant_id,

                    "quantity":
                        item.quantity,

                    "unit_price":
                        item.unit_price,

                    "subtotal":
                        subtotal,

                    "status":
                        item.status,

                    "created_at":
                        item.created_at,

                    "product_variant":
                        item.product_variant,
                }
            )


        return {
            "id":
                reservation.id,

            "reservation_code":
                reservation.reservation_code,

            "customer_id":
                reservation.customer_id,

            "branch_id":
                reservation.branch_id,

            "status":
                reservation.status,

            "notes":
                reservation.notes,

            "expires_at":
                reservation.expires_at,

            "prepared_at":
                reservation.prepared_at,

            "attended_at":
                reservation.attended_at,

            "completed_at":
                reservation.completed_at,

            "cancelled_at":
                reservation.cancelled_at,

            "created_at":
                reservation.created_at,

            "updated_at":
                reservation.updated_at,

            "is_active":
                reservation.status
                in
                ReservationService.ACTIVE_CUSTOMER_STATUSES,

            "can_cancel":
                reservation.status
                in
                ReservationService.CANCELLABLE_STATUSES,

            "total_items":
                len(
                    items
                ),

            "total_units":
                total_units,

            "total_amount":
                total_amount.quantize(
                    Decimal(
                        "0.01"
                    )
                ),

            "customer":
                reservation.customer,

            "branch":
                reservation.branch,

            "items":
                items,
        }


    # =====================================================
    # CU28 - LISTAR RESERVAS
    # =====================================================

    @staticmethod
    def list_reservations(
        db: Session,

        *,
        current_user: User,

        page: int = 1,

        page_size: int = 10,

        search: str | None = None,

        reservation_status: str | None = None,

        branch_id: int | None = None,

        customer_id: int | None = None,

        active_only: bool = False,
    ) -> dict:

        page = max(
            1,
            page,
        )


        page_size = max(
            1,
            min(
                page_size,
                100,
            ),
        )


        query = (
            ReservationService
            ._base_query(
                db
            )
            .join(
                User,

                Reservation.customer_id
                ==
                User.id,
            )
            .join(
                Branch,

                Reservation.branch_id
                ==
                Branch.id,
            )
        )


        effective_branch_id = (
            ReservationService
            ._resolve_list_branch_scope(
                db,
                current_user,
                branch_id,
            )
        )


        # =================================================
        # CLIENTE / FILTRO DE CLIENTE
        # =================================================

        if (
            ReservationService
            ._is_customer(
                current_user
            )
        ):

            query = (
                query.filter(
                    Reservation.customer_id
                    ==
                    current_user.id
                )
            )

        elif customer_id is not None:

            query = (
                query.filter(
                    Reservation.customer_id
                    ==
                    customer_id
                )
            )


        # =================================================
        # SOLO ACTIVAS (útil para "Mis reservas")
        # =================================================

        if active_only:

            query = (
                query.filter(
                    Reservation.status.in_(
                        ReservationService
                        .ACTIVE_CUSTOMER_STATUSES
                    )
                )
            )


        # =================================================
        # ESTADO
        # =================================================

        if reservation_status:

            query = (
                query.filter(
                    Reservation.status
                    ==
                    reservation_status
                )
            )


        # =================================================
        # SUCURSAL
        #
        # ADMIN: usa branch_id opcional.
        # ENCARGADO: siempre queda limitado a su sucursal.
        # CLIENTE: puede filtrar sus propias reservas por sucursal.
        # =================================================

        if effective_branch_id is not None:

            query = (
                query.filter(
                    Reservation.branch_id
                    ==
                    effective_branch_id
                )
            )


        # =================================================
        # BÚSQUEDA
        # =================================================

        if search:

            clean_search = (
                search.strip()
            )


            if clean_search:

                pattern = (
                    f"%{clean_search}%"
                )


                query = (
                    query.filter(
                        or_(
                            Reservation
                            .reservation_code
                            .ilike(
                                pattern
                            ),

                            User
                            .first_name
                            .ilike(
                                pattern
                            ),

                            User
                            .last_name
                            .ilike(
                                pattern
                            ),

                            User
                            .email
                            .ilike(
                                pattern
                            ),

                            Branch
                            .name
                            .ilike(
                                pattern
                            ),
                        )
                    )
                )


        total = (
            query.count()
        )


        total_pages = (
            math.ceil(
                total
                /
                page_size
            )
            if total > 0
            else 0
        )


        reservations = (
            query
            .order_by(
                Reservation
                .created_at
                .desc(),

                Reservation
                .id
                .desc(),
            )
            .offset(
                (
                    page
                    -
                    1
                )
                *
                page_size
            )
            .limit(
                page_size
            )
            .all()
        )


        return {
            "items": [
                ReservationService
                ._serialize(
                    reservation
                )

                for reservation
                in reservations
            ],

            "page":
                page,

            "page_size":
                page_size,

            "total":
                total,

            "total_pages":
                total_pages,
        }


    # =====================================================
    # CU28 - RESUMEN DE MIS RESERVAS (CLIENTE)
    # =====================================================

    @staticmethod
    def get_my_reservation_count(
        db: Session,

        *,
        current_user: User,
    ) -> dict:

        if not ReservationService._is_customer(current_user):
            raise PermissionError(
                "Esta operación corresponde al cliente."
            )

        grouped = (
            db.query(
                Reservation.status,
                func.count(Reservation.id),
            )
            .filter(
                Reservation.customer_id == current_user.id
            )
            .group_by(Reservation.status)
            .all()
        )

        counts = {
            status_name: int(total)
            for status_name, total in grouped
        }

        total_all = sum(counts.values())
        total_active = sum(
            counts.get(status_name, 0)
            for status_name
            in ReservationService.ACTIVE_CUSTOMER_STATUSES
        )

        return {
            "total_all": total_all,
            "total_active": total_active,
            "pending": counts.get("PENDING", 0),
            "confirmed": counts.get("CONFIRMED", 0),
            "preparing": counts.get("PREPARING", 0),
            "ready": counts.get("READY", 0),
            "attended": counts.get("ATTENDED", 0),
        }


    # =====================================================
    # CU28 - VALIDAR DUPLICADOS ACTIVOS DEL CLIENTE
    #
    # Una misma variante no puede quedar solicitada dos
    # veces por el mismo cliente en la misma sucursal
    # mientras exista una reserva activa para ella.
    # =====================================================

    @staticmethod
    def _validate_no_active_duplicate_items(
        db: Session,

        *,
        customer_id: int,
        branch_id: int,
        variant_ids: set[int],
        exclude_reservation_id: int | None = None,
    ) -> None:

        if not variant_ids:
            return

        conflict_query = (
            db.query(
                Reservation.reservation_code,
                ProductVariant.sku,
            )
            .join(
                ReservationItem,
                ReservationItem.reservation_id == Reservation.id,
            )
            .join(
                ProductVariant,
                ProductVariant.id == ReservationItem.product_variant_id,
            )
            .filter(
                Reservation.customer_id == customer_id,
                Reservation.branch_id == branch_id,
                Reservation.status.in_(
                    ReservationService.ACTIVE_CUSTOMER_STATUSES
                ),
                ReservationItem.product_variant_id.in_(variant_ids),
                ReservationItem.status.in_(
                    ReservationService.ACTIVE_ITEM_STATUSES
                ),
            )
        )

        if exclude_reservation_id is not None:
            conflict_query = conflict_query.filter(
                Reservation.id != exclude_reservation_id
            )

        conflicts = conflict_query.all()

        if not conflicts:
            return

        details = ", ".join(
            f"{sku} ({code})"
            for code, sku in conflicts
        )

        raise ValueError(
            "Ya tienes una reserva activa para esta variante "
            "en la misma sucursal. "
            f"Conflictos: {details}."
        )


    # =====================================================
    # CU28 - RESERVA PENDING DEL CLIENTE EN UNA SUCURSAL
    # =====================================================

    @staticmethod
    def get_pending_reservation_for_branch(
        db: Session,
        *,
        current_user: User,
        branch_id: int,
    ) -> dict | None:

        if not ReservationService._is_customer(current_user):
            raise PermissionError(
                "Esta operación corresponde al cliente."
            )

        reservation = (
            ReservationService._base_query(db)
            .filter(
                Reservation.customer_id == current_user.id,
                Reservation.branch_id == branch_id,
                Reservation.status == "PENDING",
            )
            .order_by(Reservation.id.desc())
            .first()
        )

        if reservation is None:
            return None

        return ReservationService._serialize(reservation)


    # =====================================================
    # CU28 - AGREGAR PRODUCTOS A UNA RESERVA PENDING
    #
    # No reinicia expires_at. Una reserva mantiene su
    # vencimiento original aunque se agreguen más prendas.
    # =====================================================

    @staticmethod
    def add_items_to_pending_reservation(
        db: Session,
        *,
        reservation_id: int,
        data: ReservationAddItems,
        current_user: User,
    ) -> dict:

        # Bloqueamos solo la fila principal para serializar dos altas
        # concurrentes sin repetir el problema de FOR UPDATE + joinedload.
        reservation = (
            db.query(Reservation)
            .filter(Reservation.id == reservation_id)
            .with_for_update()
            .first()
        )

        if reservation is None:
            raise LookupError("La reserva no existe.")

        ReservationService._validate_reservation_access(
            db,
            reservation,
            current_user,
        )

        if reservation.status != "PENDING":
            raise ValueError(
                "Solo puedes agregar productos a una reserva PENDING."
            )

        now = datetime.now(timezone.utc)
        expires_at = reservation.expires_at

        if expires_at is not None:
            if expires_at.tzinfo is None:
                expires_at = expires_at.replace(tzinfo=timezone.utc)

            if expires_at <= now:
                raise ValueError(
                    "La reserva ya venció. Actualiza tus reservas antes de agregar productos."
                )

        requested_items: dict[int, int] = {}
        for item in data.items:
            requested_items[item.product_variant_id] = (
                requested_items.get(item.product_variant_id, 0)
                + item.quantity
            )

        ReservationService._validate_no_active_duplicate_items(
            db,
            customer_id=reservation.customer_id,
            branch_id=reservation.branch_id,
            variant_ids=set(requested_items.keys()),
            exclude_reservation_id=reservation.id,
        )

        existing_items = {
            item.product_variant_id: item
            for item in (
                db.query(ReservationItem)
                .filter(ReservationItem.reservation_id == reservation.id)
                .all()
            )
        }

        added_items: list[dict] = []

        try:
            for variant_id, quantity in requested_items.items():
                variant = (
                    db.query(ProductVariant)
                    .join(Product, ProductVariant.product_id == Product.id)
                    .join(Size, ProductVariant.size_id == Size.id)
                    .join(Color, ProductVariant.color_id == Color.id)
                    .options(
                        joinedload(ProductVariant.product),
                        joinedload(ProductVariant.size),
                        joinedload(ProductVariant.color),
                    )
                    .filter(
                        ProductVariant.id == variant_id,
                        ProductVariant.is_active.is_(True),
                        Product.is_active.is_(True),
                        Size.is_active.is_(True),
                        Color.is_active.is_(True),
                    )
                    .first()
                )

                if variant is None:
                    raise LookupError(
                        f"La variante {variant_id} no existe o está inactiva."
                    )

                inventory = (
                    db.query(Inventory)
                    .filter(
                        Inventory.branch_id == reservation.branch_id,
                        Inventory.product_variant_id == variant.id,
                        Inventory.is_active.is_(True),
                    )
                    .with_for_update()
                    .first()
                )

                if inventory is None:
                    raise LookupError(
                        f"La variante {variant.sku} no tiene inventario activo en esta sucursal."
                    )

                available_quantity = (
                    inventory.stock_quantity - inventory.reserved_quantity
                )

                existing_item = existing_items.get(variant.id)

                requested_total = quantity
                if (
                    existing_item is not None
                    and existing_item.status == "PENDING"
                ):
                    requested_total += existing_item.quantity

                if available_quantity < requested_total:
                    raise ValueError(
                        f"Stock insuficiente para {variant.sku}. "
                        f"Disponible: {available_quantity}. "
                        f"Total solicitado en la reserva: {requested_total}."
                    )

                if existing_item is not None:
                    if existing_item.status == "RESERVED":
                        raise ValueError(
                            f"La variante {variant.sku} ya fue apartada físicamente. "
                            "No puedes aumentar su cantidad desde la web."
                        )

                    if existing_item.status != "PENDING":
                        raise ValueError(
                            f"La variante {variant.sku} ya no admite cambios en esta reserva."
                        )

                    existing_item.quantity += quantity
                    item_id = existing_item.id
                    final_quantity = existing_item.quantity
                else:
                    unit_price = (
                        Decimal(variant.product.base_price)
                        + Decimal(variant.additional_price or 0)
                    ).quantize(Decimal("0.01"))

                    new_item = ReservationItem(
                        reservation_id=reservation.id,
                        product_variant_id=variant.id,
                        quantity=quantity,
                        unit_price=unit_price,
                        status="PENDING",
                    )
                    db.add(new_item)
                    db.flush()
                    existing_items[variant.id] = new_item
                    item_id = new_item.id
                    final_quantity = new_item.quantity

                added_items.append(
                    {
                        "reservation_item_id": item_id,
                        "product_variant_id": variant.id,
                        "added_quantity": quantity,
                        "final_quantity": final_quantity,
                    }
                )

            if data.notes and data.notes.strip():
                current_notes = (reservation.notes or "").strip()
                extra_notes = data.notes.strip()
                reservation.notes = (
                    f"{current_notes}\n{extra_notes}"
                    if current_notes
                    else extra_notes
                )

            ReservationService._create_audit_log(
                db,
                user_id=current_user.id,
                action="ADD_RESERVATION_ITEMS",
                reservation=reservation,
                description=(
                    "Se agregaron productos a la reserva "
                    f"{reservation.reservation_code}."
                ),
                new_values={
                    "items": added_items,
                    "expires_at": (
                        reservation.expires_at.isoformat()
                        if reservation.expires_at is not None
                        else None
                    ),
                },
            )

            db.commit()

        except Exception:
            db.rollback()
            raise

        updated = ReservationService._get_reservation(db, reservation.id)
        return ReservationService._serialize(updated)


    # =====================================================
    # CU28 - CONSULTAR RESERVA
    # =====================================================

    @staticmethod
    def get_reservation(
        db: Session,

        *,
        reservation_id: int,

        current_user: User,
    ) -> dict:

        reservation = (
            ReservationService
            ._get_reservation(
                db,
                reservation_id,
            )
        )


        ReservationService._validate_reservation_access(
            db,
            reservation,
            current_user,
        )


        return (
            ReservationService
            ._serialize(
                reservation
            )
        )


    # =====================================================
    # CU28 - CREAR RESERVA
    # =====================================================

    @staticmethod
    def create_reservation(
        db: Session,

        *,
        data: ReservationCreate,

        current_user: User,
    ) -> dict:

        # =================================================
        # CLIENTE
        # =================================================

        if (
            ReservationService
            ._is_customer(
                current_user
            )
        ):

            if (
                data.customer_id
                is not None
                and
                data.customer_id
                !=
                current_user.id
            ):

                raise PermissionError(
                    "No puedes crear una reserva "
                    "para otro cliente."
                )


            customer_id = (
                current_user.id
            )

        else:

            if data.customer_id is None:

                raise ValueError(
                    "Debes indicar customer_id "
                    "para crear la reserva."
                )


            customer_id = (
                data.customer_id
            )


            role = (
                ReservationService
                ._role_name(
                    current_user
                )
            )

            if role == ReservationService.MANAGER_ROLE:

                manager_branch_id = (
                    ReservationService
                    ._get_manager_branch_id(
                        db,
                        current_user,
                    )
                )

                if data.branch_id != manager_branch_id:
                    raise PermissionError(
                        "No puedes crear reservas "
                        "para otra sucursal."
                    )

            elif role not in ReservationService.ADMIN_ROLES:
                raise PermissionError(
                    "Tu rol no puede crear reservas "
                    "para otros clientes."
                )


        customer = (
            db.query(
                User
            )
            .options(
                joinedload(
                    User.role
                )
            )
            .filter(
                User.id
                ==
                customer_id,

                User.is_active.is_(
                    True
                ),
            )
            .first()
        )


        if customer is None:

            raise LookupError(
                "El cliente no existe "
                "o está inactivo."
            )


        if (
            customer.role is None
            or
            customer.role.name
            !=
            ReservationService.CUSTOMER_ROLE
        ):

            raise ValueError(
                "El usuario seleccionado "
                "no tiene rol CLIENTE."
            )


        # =================================================
        # SUCURSAL
        # =================================================

        branch = (
            db.query(
                Branch
            )
            .filter(
                Branch.id
                ==
                data.branch_id,

                Branch.is_active.is_(
                    True
                ),
            )
            .first()
        )


        if branch is None:

            raise LookupError(
                "La sucursal no existe "
                "o está inactiva."
            )


        # =================================================
        # EXPIRACIÓN
        # =================================================

        # Regla de negocio:
        # una solicitud PENDING todavía NO empieza a consumir
        # el plazo de retiro. El expires_at se asigna recién
        # cuando el encargado confirma la reserva.
        expires_at = None


        # =================================================
        # UNA SOLA RESERVA PENDING POR CLIENTE + SUCURSAL
        # =================================================

        # Serializa creaciones concurrentes del mismo cliente para evitar
        # dos reservas PENDING simultáneas en la misma sucursal.
        (
            db.query(User.id)
            .filter(User.id == customer.id)
            .with_for_update()
            .one()
        )

        existing_pending = (
            db.query(Reservation)
            .filter(
                Reservation.customer_id == customer.id,
                Reservation.branch_id == branch.id,
                Reservation.status == "PENDING",
            )
            .order_by(Reservation.id.desc())
            .first()
        )

        if existing_pending is not None:
            raise ValueError(
                "Ya tienes una reserva PENDING en esta sucursal. "
                f"Agrega los nuevos productos a la reserva "
                f"{existing_pending.reservation_code}."
            )

        # =================================================
        # AGRUPAR VARIANTES
        # =================================================

        requested_items: dict[
            int,
            int,
        ] = {}


        for item in data.items:

            requested_items[
                item.product_variant_id
            ] = (
                requested_items.get(
                    item.product_variant_id,
                    0,
                )
                +
                item.quantity
            )


        ReservationService._validate_no_active_duplicate_items(
            db,
            customer_id=customer.id,
            branch_id=branch.id,
            variant_ids=set(requested_items.keys()),
        )


        try:

            reservation = Reservation(
                reservation_code=
                    ReservationService
                    ._generate_code(),

                customer_id=
                    customer.id,

                branch_id=
                    branch.id,

                status=
                    "PENDING",

                notes=
                    data.notes,

                expires_at=
                    expires_at,
            )


            db.add(
                reservation
            )

            db.flush()


            # =================================================
            # REGISTRAR SOLICITUDES
            #
            # CU29:
            # todavía NO reservamos stock.
            # =================================================

            for (
                variant_id,
                quantity,
            ) in requested_items.items():

                variant = (
                    db.query(
                        ProductVariant
                    )
                    .join(
                        Product,

                        ProductVariant.product_id
                        ==
                        Product.id,
                    )
                    .join(
                        Size,

                        ProductVariant.size_id
                        ==
                        Size.id,
                    )
                    .join(
                        Color,

                        ProductVariant.color_id
                        ==
                        Color.id,
                    )
                    .options(
                        joinedload(
                            ProductVariant.product
                        ),

                        joinedload(
                            ProductVariant.size
                        ),

                        joinedload(
                            ProductVariant.color
                        ),
                    )
                    .filter(
                        ProductVariant.id
                        ==
                        variant_id,

                        ProductVariant
                        .is_active
                        .is_(
                            True
                        ),

                        Product
                        .is_active
                        .is_(
                            True
                        ),

                        Size
                        .is_active
                        .is_(
                            True
                        ),

                        Color
                        .is_active
                        .is_(
                            True
                        ),
                    )
                    .first()
                )


                if variant is None:

                    raise LookupError(
                        f"La variante {variant_id} "
                        f"no existe o está inactiva."
                    )


                inventory = (
                    db.query(
                        Inventory
                    )
                    .filter(
                        Inventory.branch_id
                        ==
                        branch.id,

                        Inventory
                        .product_variant_id
                        ==
                        variant.id,

                        Inventory
                        .is_active
                        .is_(
                            True
                        ),
                    )
                    .first()
                )


                if inventory is None:

                    raise LookupError(
                        f"La variante {variant.sku} "
                        f"no tiene inventario activo "
                        f"en esta sucursal."
                    )


                available_quantity = (
                    inventory.stock_quantity
                    -
                    inventory.reserved_quantity
                )


                if (
                    available_quantity
                    <
                    quantity
                ):

                    raise ValueError(
                        f"Stock insuficiente para "
                        f"{variant.sku}. "
                        f"Disponible: "
                        f"{available_quantity}. "
                        f"Solicitado: "
                        f"{quantity}."
                    )


                unit_price = (
                    Decimal(
                        variant.product.base_price
                    )
                    +
                    Decimal(
                        variant.additional_price
                        or 0
                    )
                ).quantize(
                    Decimal(
                        "0.01"
                    )
                )


                reservation_item = (
                    ReservationItem(
                        reservation_id=
                            reservation.id,

                        product_variant_id=
                            variant.id,

                        quantity=
                            quantity,

                        unit_price=
                            unit_price,

                        status=
                            "PENDING",
                    )
                )


                db.add(
                    reservation_item
                )


            db.commit()


        except Exception:

            db.rollback()

            raise


        created = (
            ReservationService
            ._get_reservation(
                db,
                reservation.id,
            )
        )


        return (
            ReservationService
            ._serialize(
                created
            )
        )


    # =====================================================
    # CU29 - VINCULAR / APARTAR PRENDAS
    # =====================================================

    @staticmethod
    def link_reserved_items(
        db: Session,

        *,
        reservation_id: int,

        current_user: User,
    ) -> dict:

        reservation = (
            ReservationService
            ._get_reservation(
                db,
                reservation_id,
            )
        )


        ReservationService._validate_staff_management_access(
            db,
            reservation,
            current_user,
        )


        # =================================================
        # PRECONDICIÓN CU29
        # =================================================

        if (
            reservation.status
            !=
            "PENDING"
        ):

            raise ValueError(
                "Solo una reserva PENDING "
                "puede vincular sus prendas."
            )


        pending_items = [
            item
            for item
            in reservation.items
            if item.status
            ==
            "PENDING"
        ]


        if not pending_items:

            raise ValueError(
                "La reserva no tiene prendas "
                "pendientes de vinculación."
            )


        try:

            linked_items = []


            # =================================================
            # BLOQUEAR Y VALIDAR TODO
            # =================================================

            inventories: dict[
                int,
                Inventory,
            ] = {}


            for item in pending_items:

                inventory = (
                    db.query(
                        Inventory
                    )
                    .filter(
                        Inventory.branch_id
                        ==
                        reservation.branch_id,

                        Inventory
                        .product_variant_id
                        ==
                        item.product_variant_id,

                        Inventory
                        .is_active
                        .is_(
                            True
                        ),
                    )
                    .with_for_update()
                    .first()
                )


                if inventory is None:

                    raise LookupError(
                        "No existe inventario activo "
                        "para una de las prendas "
                        "solicitadas."
                    )


                available_quantity = (
                    inventory.stock_quantity
                    -
                    inventory.reserved_quantity
                )


                if (
                    available_quantity
                    <
                    item.quantity
                ):

                    raise ValueError(
                        f"Stock insuficiente para "
                        f"{item.product_variant.sku}. "
                        f"Disponible: "
                        f"{available_quantity}. "
                        f"Solicitado: "
                        f"{item.quantity}."
                    )


                inventories[
                    item.id
                ] = inventory


            # =================================================
            # VINCULAR TODAS LAS PRENDAS
            # =================================================

            for item in pending_items:

                inventory = (
                    inventories[
                        item.id
                    ]
                )


                reserved_before = (
                    inventory
                    .reserved_quantity
                )


                reserved_after = (
                    reserved_before
                    +
                    item.quantity
                )


                inventory.reserved_quantity = (
                    reserved_after
                )


                item.status = (
                    "RESERVED"
                )


                ReservationService._create_inventory_movement(
                    db,

                    inventory=
                        inventory,

                    reservation=
                        reservation,

                    movement_type=
                        "RESERVE",

                    quantity=
                        item.quantity,

                    reserved_before=
                        reserved_before,

                    reserved_after=
                        reserved_after,

                    user_id=
                        current_user.id,

                    reason=
                        "Vinculación física de prendas "
                        "a la reserva.",
                )


                linked_items.append(
                    {
                        "reservation_item_id":
                            item.id,

                        "product_variant_id":
                            item.product_variant_id,

                        "quantity":
                            item.quantity,

                        "status":
                            "RESERVED",
                    }
                )


            # =================================================
            # AUDITORÍA CU29
            # =================================================

            ReservationService._create_audit_log(
                db,

                user_id=
                    current_user.id,

                action=
                    "LINK_RESERVED_ITEMS",

                reservation=
                    reservation,

                description=(
                    "Se vincularon y apartaron "
                    "físicamente las prendas "
                    f"de la reserva "
                    f"{reservation.reservation_code}."
                ),

                old_values={
                    "items_status":
                        "PENDING",
                },

                new_values={
                    "items_status":
                        "RESERVED",

                    "items":
                        linked_items,
                },
            )


            db.commit()


        except Exception:

            db.rollback()

            raise


        updated = (
            ReservationService
            ._get_reservation(
                db,
                reservation.id,
            )
        )


        return (
            ReservationService
            ._serialize(
                updated
            )
        )


    # =====================================================
    # CU28 - CONFIRMAR RESERVA
    # =====================================================

    @staticmethod
    def confirm_reservation(
        db: Session,

        *,
        reservation_id: int,

        current_user: User,
    ) -> dict:

        reservation = (
            ReservationService
            ._get_reservation(
                db,
                reservation_id,
            )
        )


        ReservationService._validate_staff_management_access(
            db,
            reservation,
            current_user,
        )


        if (
            reservation.status
            !=
            "PENDING"
        ):

            raise ValueError(
                "Solo una reserva PENDING "
                "puede ser confirmada."
            )


        # =================================================
        # CU29 DEBE HABER TERMINADO
        # =================================================

        if not reservation.items:

            raise ValueError(
                "La reserva no tiene prendas."
            )


        pending_items = [
            item
            for item
            in reservation.items
            if item.status
            !=
            "RESERVED"
        ]


        if pending_items:

            raise ValueError(
                "Debes vincular todas las prendas "
                "antes de confirmar la reserva."
            )


        old_status = (
            reservation.status
        )


        try:

            confirmed_at = datetime.now(timezone.utc)

            reservation.status = (
                "CONFIRMED"
            )

            # El plazo para recoger/pagar presencialmente empieza
            # exactamente cuando la sucursal confirma la reserva.
            reservation.expires_at = (
                confirmed_at
                + timedelta(hours=settings.reservation_ttl_hours)
            )

            NotificationService.notify_reservation_status(
                db,
                reservation=reservation,
                status="CONFIRMED",
            )


            ReservationService._create_audit_log(
                db,

                user_id=
                    current_user.id,

                action=
                    "CONFIRM_RESERVATION",

                reservation=
                    reservation,

                description=(
                    "Se confirmó la reserva "
                    f"{reservation.reservation_code}."
                ),

                old_values={
                    "status":
                        old_status,
                },

                new_values={
                    "status":
                        "CONFIRMED",

                    "expires_at":
                        reservation.expires_at.isoformat(),

                    "reservation_ttl_hours":
                        settings.reservation_ttl_hours,
                },
            )


            db.commit()


        except Exception:

            db.rollback()

            raise


        updated = (
            ReservationService
            ._get_reservation(
                db,
                reservation.id,
            )
        )


        # El correo es una notificación secundaria: si Brevo falla,
        # la confirmación NO se revierte. La reserva ya quedó
        # CONFIRMED y con su expires_at persistido.
        customer_email = (updated.customer.email or "").strip()

        if customer_email and "@" in customer_email:
            try:
                EmailService.send_reservation_confirmed(
                    email=customer_email,
                    first_name=updated.customer.first_name,
                    reservation_code=updated.reservation_code,
                    branch_name=updated.branch.name,
                    branch_address=updated.branch.address,
                    expires_at=updated.expires_at,
                    ttl_hours=settings.reservation_ttl_hours,
                )
            except Exception:
                logger.exception(
                    "No se pudo enviar el correo de confirmación "
                    "de la reserva %s al cliente %s.",
                    updated.reservation_code,
                    updated.customer_id,
                )


        return (
            ReservationService
            ._serialize(
                updated
            )
        )


    # =====================================================
    # LIBERAR ITEMS
    # =====================================================

    @staticmethod
    def _release_items(
        db: Session,

        *,
        reservation: Reservation,

        current_user_id: int | None,

        reason: str,
    ) -> None:

        released_items = []


        for item in reservation.items:

            # =================================================
            # PENDIENTE
            #
            # Nunca modificó inventario.
            # =================================================

            if (
                item.status
                ==
                "PENDING"
            ):

                item.status = (
                    "RELEASED"
                )


                released_items.append(
                    {
                        "reservation_item_id":
                            item.id,

                        "product_variant_id":
                            item.product_variant_id,

                        "quantity":
                            item.quantity,

                        "inventory_released":
                            False,
                    }
                )


                continue


            # =================================================
            # YA LIBERADO / CONSUMIDO
            # =================================================

            if (
                item.status
                !=
                "RESERVED"
            ):

                continue


            inventory = (
                db.query(
                    Inventory
                )
                .filter(
                    Inventory.branch_id
                    ==
                    reservation.branch_id,

                    Inventory
                    .product_variant_id
                    ==
                    item.product_variant_id,

                    Inventory
                    .is_active
                    .is_(
                        True
                    ),
                )
                .with_for_update()
                .first()
            )


            if inventory is None:

                raise LookupError(
                    "No se encontró el inventario "
                    "de una prenda reservada."
                )


            reserved_before = (
                inventory
                .reserved_quantity
            )


            if (
                reserved_before
                <
                item.quantity
            ):

                raise ValueError(
                    "La cantidad reservada "
                    "del inventario es inconsistente."
                )


            reserved_after = (
                reserved_before
                -
                item.quantity
            )


            inventory.reserved_quantity = (
                reserved_after
            )


            item.status = (
                "RELEASED"
            )


            ReservationService._create_inventory_movement(
                db,

                inventory=
                    inventory,

                reservation=
                    reservation,

                movement_type=
                    "RELEASE",

                quantity=
                    item.quantity,

                reserved_before=
                    reserved_before,

                reserved_after=
                    reserved_after,

                user_id=
                    current_user_id,

                reason=
                    reason,
            )


            released_items.append(
                {
                    "reservation_item_id":
                        item.id,

                    "product_variant_id":
                        item.product_variant_id,

                    "quantity":
                        item.quantity,

                    "inventory_released":
                        True,
                }
            )


        ReservationService._create_audit_log(
            db,

            user_id=
                current_user_id,

            action=
                "RELEASE_RESERVED_ITEMS",

            reservation=
                reservation,

            description=(
                "Se liberaron las prendas "
                f"de la reserva "
                f"{reservation.reservation_code}."
            ),

            new_values={
                "items":
                    released_items,
            },
        )


    # =====================================================
    # CU28 / CU29 - CANCELAR
    # =====================================================

    @staticmethod
    def cancel_reservation(
        db: Session,

        *,
        reservation_id: int,

        current_user: User,

        reason: str | None = None,
    ) -> dict:

        reservation = (
            ReservationService
            ._get_reservation(
                db,
                reservation_id,
            )
        )


        ReservationService._validate_reservation_access(
            db,
            reservation,
            current_user,
        )


        if (
            reservation.status
            not in
            ReservationService
            .CANCELLABLE_STATUSES
        ):

            raise ValueError(
                "Solo una reserva PENDING "
                "o CONFIRMED puede cancelarse."
            )


        try:

            ReservationService._release_items(
                db,

                reservation=
                    reservation,

                current_user_id=
                    current_user.id,

                reason=(
                    reason
                    or
                    "Cancelación de reserva."
                ),
            )


            old_status = (
                reservation.status
            )


            reservation.status = (
                "CANCELLED"
            )


            reservation.cancelled_at = (
                datetime.now(
                    timezone.utc
                )
            )


            if reason:

                current_notes = (
                    reservation.notes
                    or
                    ""
                )


                if current_notes:

                    current_notes += (
                        "\n"
                    )


                reservation.notes = (
                    current_notes
                    +
                    "Motivo de cancelación: "
                    +
                    reason
                )


            NotificationService.notify_reservation_status(
                db,
                reservation=reservation,
                status="CANCELLED",
                reason=reason.strip() if reason and reason.strip() else None,
            )


            ReservationService._create_audit_log(
                db,

                user_id=
                    current_user.id,

                action=
                    "CANCEL_RESERVATION",

                reservation=
                    reservation,

                description=(
                    "Se canceló la reserva "
                    f"{reservation.reservation_code}."
                ),

                old_values={
                    "status":
                        old_status,
                },

                new_values={
                    "status":
                        "CANCELLED",
                },
            )


            db.commit()


        except Exception:

            db.rollback()

            raise


        updated = (
            ReservationService
            ._get_reservation(
                db,
                reservation.id,
            )
        )


        return (
            ReservationService
            ._serialize(
                updated
            )
        )


    # =====================================================
    # CU29 - VENCER RESERVA
    #
    # Este método puede ser llamado luego por un job,
    # scheduler o tarea periódica.
    # =====================================================

    @staticmethod
    def expire_reservation(
        db: Session,

        *,
        reservation_id: int,

        system_user_id: int | None = None,
    ) -> dict:

        reservation = (
            ReservationService
            ._get_reservation(
                db,
                reservation_id,
            )
        )


        if (
            reservation.status
            not in ReservationService.EXPIRABLE_STATUSES
        ):

            raise ValueError(
                "La reserva no puede vencer "
                "desde su estado actual."
            )


        now = (
            datetime.now(
                timezone.utc
            )
        )


        if reservation.expires_at is None:
            raise ValueError(
                "La reserva todavía no tiene fecha de vencimiento. "
                "El plazo empieza cuando la reserva es confirmada."
            )

        expires_at = reservation.expires_at


        if (
            expires_at.tzinfo
            is None
        ):

            expires_at = (
                expires_at.replace(
                    tzinfo=
                        timezone.utc
                )
            )


        if (
            expires_at
            >
            now
        ):

            raise ValueError(
                "La reserva todavía no venció."
            )


        try:

            ReservationService._release_items(
                db,

                reservation=
                    reservation,

                current_user_id=
                    system_user_id,

                reason=
                    "Vencimiento automático "
                    "de reserva.",
            )


            old_status = (
                reservation.status
            )


            reservation.status = (
                "EXPIRED"
            )

            NotificationService.notify_reservation_status(
                db,
                reservation=reservation,
                status="EXPIRED",
            )


            ReservationService._create_audit_log(
                db,

                user_id=
                    system_user_id,

                action=
                    "EXPIRE_RESERVATION",

                reservation=
                    reservation,

                description=(
                    "La reserva "
                    f"{reservation.reservation_code} "
                    "venció y sus prendas "
                    "fueron liberadas."
                ),

                old_values={
                    "status":
                        old_status,
                },

                new_values={
                    "status":
                        "EXPIRED",
                },
            )


            db.commit()


        except Exception:

            db.rollback()

            raise


        updated = (
            ReservationService
            ._get_reservation(
                db,
                reservation.id,
            )
        )


        return (
            ReservationService
            ._serialize(
                updated
            )
        )

    # =====================================================
    # CU30 / CU31 - CAMBIAR ESTADO OPERATIVO
    #
    # Flujo permitido:
    #
    # CONFIRMED -> PREPARING
    # PREPARING -> READY
    # READY -> ATTENDED
    # ATTENDED -> COMPLETED
    #
    # No se permiten saltos de estado.
    # =====================================================

    @staticmethod
    def update_operational_status(
        db: Session,

        *,
        reservation_id: int,

        new_status: str,

        current_user: User,
    ) -> dict:

        reservation = (
            ReservationService
            ._get_reservation(
                db,
                reservation_id,
            )
        )


        ReservationService._validate_staff_management_access(
            db,
            reservation,
            current_user,
        )


        # =================================================
        # TRANSICIONES PERMITIDAS
        # =================================================

        allowed_transitions = {
            "CONFIRMED":
                "PREPARING",

            "PREPARING":
                "READY",

            "READY":
                "ATTENDED",

            "ATTENDED":
                "COMPLETED",
        }


        expected_status = (
            allowed_transitions
            .get(
                reservation.status
            )
        )


        if expected_status is None:

            raise ValueError(
                "La reserva en estado "
                f"{reservation.status} "
                "no admite un cambio operativo."
            )


        if (
            new_status
            !=
            expected_status
        ):

            raise ValueError(
                "Transición inválida: "
                f"{reservation.status} "
                "-> "
                f"{new_status}. "
                "El siguiente estado permitido es "
                f"{expected_status}."
            )


        old_status = (
            reservation.status
        )


        now = (
            datetime.now(
                timezone.utc
            )
        )


        try:

            # =============================================
            # CU31
            # CONFIRMED -> PREPARING
            # =============================================

            if (
                new_status
                ==
                "PREPARING"
            ):

                reservation.status = (
                    "PREPARING"
                )


            # =============================================
            # CU31
            # PREPARING -> READY
            # =============================================

            elif (
                new_status
                ==
                "READY"
            ):

                reservation.status = (
                    "READY"
                )

                reservation.prepared_at = (
                    now
                )


            # =============================================
            # CU30
            # READY -> ATTENDED
            # =============================================

            elif (
                new_status
                ==
                "ATTENDED"
            ):

                reservation.status = (
                    "ATTENDED"
                )

                reservation.attended_at = (
                    now
                )


            # =============================================
            # CU30
            # ATTENDED -> COMPLETED
            #
            # IMPORTANTE:
            # aquí NO consumimos inventario todavía.
            # El consumo definitivo debe quedar ligado
            # a la venta / operación comercial correspondiente.
            # =============================================

            elif (
                new_status
                ==
                "COMPLETED"
            ):

                reservation.status = (
                    "COMPLETED"
                )

                reservation.completed_at = (
                    now
                )


            NotificationService.notify_reservation_status(
                db,
                reservation=reservation,
                status=new_status,
            )


            # =============================================
            # AUDITORÍA
            # =============================================

            action_by_status = {
                "PREPARING":
                    "START_RESERVATION_PREPARATION",

                "READY":
                    "MARK_RESERVATION_READY",

                "ATTENDED":
                    "MARK_RESERVATION_ATTENDED",

                "COMPLETED":
                    "COMPLETE_RESERVATION",
            }


            ReservationService._create_audit_log(
                db,

                user_id=
                    current_user.id,

                action=
                    action_by_status[
                        new_status
                    ],

                reservation=
                    reservation,

                description=(
                    "Se actualizó el estado de la reserva "
                    f"{reservation.reservation_code} "
                    f"de {old_status} a {new_status}."
                ),

                old_values={
                    "status":
                        old_status,
                },

                new_values={
                    "status":
                        new_status,

                    "prepared_at":
                        (
                            reservation
                            .prepared_at
                            .isoformat()
                            if
                            reservation
                            .prepared_at
                            is not None
                            else
                            None
                        ),

                    "attended_at":
                        (
                            reservation
                            .attended_at
                            .isoformat()
                            if
                            reservation
                            .attended_at
                            is not None
                            else
                            None
                        ),

                    "completed_at":
                        (
                            reservation
                            .completed_at
                            .isoformat()
                            if
                            reservation
                            .completed_at
                            is not None
                            else
                            None
                        ),
                },
            )


            db.commit()


        except Exception:

            db.rollback()

            raise


        updated = (
            ReservationService
            ._get_reservation(
                db,
                reservation.id,
            )
        )


        return (
            ReservationService
            ._serialize(
                updated
            )
        )



    # =====================================================
    # ASISTENTE CLIENTE - ACTUALIZAR ÍTEM PENDING
    # =====================================================

    @staticmethod
    def update_pending_item_quantity(
        db: Session,
        *,
        reservation_id: int,
        reservation_item_id: int,
        quantity: int,
        current_user: User,
    ) -> dict:
        if quantity <= 0:
            raise ValueError("La cantidad debe ser mayor a cero.")

        reservation = (
            db.query(Reservation)
            .filter(Reservation.id == reservation_id)
            .with_for_update()
            .first()
        )
        if reservation is None:
            raise LookupError("La reserva no existe.")

        ReservationService._validate_reservation_access(db, reservation, current_user)
        if reservation.status != "PENDING":
            raise ValueError("Solo puedes modificar productos de una reserva PENDING.")

        item = (
            db.query(ReservationItem)
            .filter(
                ReservationItem.id == reservation_item_id,
                ReservationItem.reservation_id == reservation.id,
            )
            .with_for_update()
            .first()
        )
        if item is None:
            raise LookupError("El producto no pertenece a esta reserva.")
        if item.status != "PENDING":
            raise ValueError("Este producto de la reserva ya no admite cambios.")

        inventory = (
            db.query(Inventory)
            .filter(
                Inventory.branch_id == reservation.branch_id,
                Inventory.product_variant_id == item.product_variant_id,
                Inventory.is_active.is_(True),
            )
            .with_for_update()
            .first()
        )
        if inventory is None:
            raise LookupError("No existe inventario activo para esta variante en la sucursal.")

        available = inventory.stock_quantity - inventory.reserved_quantity
        if quantity > available:
            raise ValueError(f"Solo hay {available} unidades disponibles para esta variante.")

        old_quantity = item.quantity
        try:
            item.quantity = quantity
            ReservationService._create_audit_log(
                db,
                user_id=current_user.id,
                action="UPDATE_RESERVATION_ITEM_QUANTITY",
                reservation=reservation,
                description=f"Se actualizó la cantidad de un producto de {reservation.reservation_code}.",
                old_values={"reservation_item_id": item.id, "quantity": old_quantity},
                new_values={"reservation_item_id": item.id, "quantity": quantity},
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        updated = ReservationService._get_reservation(db, reservation.id)
        return ReservationService._serialize(updated)


    # =====================================================
    # ASISTENTE CLIENTE - QUITAR ÍTEM PENDING
    # =====================================================

    @staticmethod
    def remove_pending_item(
        db: Session,
        *,
        reservation_id: int,
        reservation_item_id: int,
        current_user: User,
    ) -> dict:
        reservation = (
            db.query(Reservation)
            .filter(Reservation.id == reservation_id)
            .with_for_update()
            .first()
        )
        if reservation is None:
            raise LookupError("La reserva no existe.")

        ReservationService._validate_reservation_access(db, reservation, current_user)
        if reservation.status != "PENDING":
            raise ValueError("Solo puedes quitar productos de una reserva PENDING.")

        items = (
            db.query(ReservationItem)
            .filter(ReservationItem.reservation_id == reservation.id)
            .all()
        )
        item = next((row for row in items if row.id == reservation_item_id), None)
        if item is None:
            raise LookupError("El producto no pertenece a esta reserva.")
        if item.status != "PENDING":
            raise ValueError("Este producto de la reserva ya no admite cambios.")
        if len(items) <= 1:
            raise ValueError(
                "No puedes dejar una reserva sin productos. Cancela la reserva si ya no deseas conservarla."
            )

        try:
            old_values = {
                "reservation_item_id": item.id,
                "product_variant_id": item.product_variant_id,
                "quantity": item.quantity,
            }
            db.delete(item)
            ReservationService._create_audit_log(
                db,
                user_id=current_user.id,
                action="REMOVE_RESERVATION_ITEM",
                reservation=reservation,
                description=f"Se quitó un producto de la reserva {reservation.reservation_code}.",
                old_values=old_values,
                new_values=None,
            )
            db.commit()
        except Exception:
            db.rollback()
            raise

        updated = ReservationService._get_reservation(db, reservation.id)
        return ReservationService._serialize(updated)
