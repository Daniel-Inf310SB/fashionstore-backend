from __future__ import annotations

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from decimal import Decimal

from sqlalchemy import select

from sqlalchemy.orm import Session

from app.models.branch import Branch

from app.models.inventory import Inventory

from app.models.inventory_movement import (
    InventoryMovement,
)

from app.models.product import Product

from app.models.product_variant import (
    ProductVariant,
)

from app.models.reservation import Reservation

from app.models.reservation_item import (
    ReservationItem,
)

from app.models.user import User


# =========================================================
# CONFIGURACIÓN
# =========================================================

SEED_RESERVATION_PREFIX = (
    "RSV-SEED"
)


# =========================================================
# MONEY
# =========================================================

def _money(
    value,
) -> Decimal:

    return Decimal(
        str(
            value
        )
    ).quantize(
        Decimal(
            "0.01"
        )
    )


# =========================================================
# CLIENTE
# =========================================================

def _get_customer(
    db: Session,

    email: str,
) -> User:

    customer = db.scalar(
        select(
            User
        )
        .where(
            User.email
            ==
            email
        )
    )


    if customer is None:

        raise RuntimeError(
            f"No existe el cliente {email}. "
            "Ejecuta seed_customers primero."
        )


    return customer


# =========================================================
# INVENTARIO DISPONIBLE
# =========================================================

def _get_available_inventory(
    db: Session,

    *,
    excluded_inventory_ids: set[int],

    minimum_available: int = 5,
) -> Inventory:

    inventories = list(
        db.scalars(
            select(
                Inventory
            )
            .where(
                Inventory
                .is_active
                .is_(
                    True
                ),

                Inventory.stock_quantity
                -
                Inventory.reserved_quantity
                >=
                minimum_available,
            )
            .order_by(
                Inventory.id
            )
        ).all()
    )


    for inventory in inventories:

        if (
            inventory.id
            not in
            excluded_inventory_ids
        ):

            return inventory


    raise RuntimeError(
        "No se encontró inventario suficiente "
        "para generar las reservas seed."
    )


# =========================================================
# PRECIO DE VARIANTE
# =========================================================

def _get_variant_price(
    db: Session,

    variant_id: int,
) -> Decimal:

    row = db.execute(
        select(
            Product.base_price,

            ProductVariant
            .additional_price,
        )
        .join(
            ProductVariant,

            ProductVariant.product_id
            ==
            Product.id,
        )
        .where(
            ProductVariant.id
            ==
            variant_id
        )
    ).first()


    if row is None:

        raise RuntimeError(
            f"No existe la variante "
            f"{variant_id}."
        )


    base_price, additional_price = (
        row
    )


    return _money(
        Decimal(
            base_price
        )
        +
        Decimal(
            additional_price
            or 0
        )
    )


# =========================================================
# MOVIMIENTO DE INVENTARIO
# =========================================================

def _create_inventory_movement(
    db: Session,

    *,
    inventory: Inventory,

    movement_type: str,

    quantity: int,

    reserved_before: int,

    reserved_after: int,

    user_id: int,

    reservation: Reservation,

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
            reservation
            .reservation_code,

        reason=
            reason,

        notes=(
            "Movimiento generado por "
            "seed de reservas."
        ),
    )


    db.add(
        movement
    )


# =========================================================
# CU28 - CREAR ITEM PENDIENTE
#
# Se registra la solicitud, pero todavía NO se modifica
# reserved_quantity.
#
# Es el escenario necesario para probar CU29.
# =========================================================

def _create_pending_item(
    db: Session,

    *,
    reservation: Reservation,

    inventory: Inventory,

    quantity: int,
) -> ReservationItem:

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

        raise RuntimeError(
            f"Inventario {inventory.id} "
            "sin disponibilidad suficiente."
        )


    unit_price = (
        _get_variant_price(
            db,

            inventory
            .product_variant_id,
        )
    )


    item = ReservationItem(
        reservation_id=
            reservation.id,

        product_variant_id=
            inventory
            .product_variant_id,

        quantity=
            quantity,

        unit_price=
            unit_price,

        status=
            "PENDING",
    )


    db.add(
        item
    )


    return item


# =========================================================
# CU29 - CREAR ITEM YA RESERVADO
#
# Representa una reserva donde el encargado ya apartó
# físicamente las prendas.
#
# reserved_quantity += quantity
# InventoryMovement = RESERVE
# =========================================================

def _reserve_item(
    db: Session,

    *,
    reservation: Reservation,

    inventory: Inventory,

    quantity: int,
) -> ReservationItem:

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

        raise RuntimeError(
            f"Inventario {inventory.id} "
            "sin disponibilidad suficiente."
        )


    unit_price = (
        _get_variant_price(
            db,

            inventory
            .product_variant_id,
        )
    )


    item = ReservationItem(
        reservation_id=
            reservation.id,

        product_variant_id=
            inventory
            .product_variant_id,

        quantity=
            quantity,

        unit_price=
            unit_price,

        status=
            "RESERVED",
    )


    db.add(
        item
    )


    reserved_before = (
        inventory
        .reserved_quantity
    )


    reserved_after = (
        reserved_before
        +
        quantity
    )


    inventory.reserved_quantity = (
        reserved_after
    )


    _create_inventory_movement(
        db,

        inventory=
            inventory,

        movement_type=
            "RESERVE",

        quantity=
            quantity,

        reserved_before=
            reserved_before,

        reserved_after=
            reserved_after,

        user_id=
            reservation.customer_id,

        reservation=
            reservation,

        reason=(
            "Apartado de prendas "
            "generado por seed CU29."
        ),
    )


    return item


# =========================================================
# CU29 - LIBERAR ITEM RESERVADO
#
# reserved_quantity -= quantity
# item = RELEASED
# InventoryMovement = RELEASE
# =========================================================

def _release_reserved_item(
    db: Session,

    *,
    reservation: Reservation,

    inventory: Inventory,

    item: ReservationItem,

    reason: str,
) -> None:

    if (
        item.status
        !=
        "RESERVED"
    ):

        raise RuntimeError(
            "Solo se puede liberar un item "
            "que se encuentre RESERVED."
        )


    reserved_before = (
        inventory
        .reserved_quantity
    )


    reserved_after = (
        reserved_before
        -
        item.quantity
    )


    if (
        reserved_after
        <
        0
    ):

        raise RuntimeError(
            "El stock reservado no puede "
            "quedar negativo."
        )


    inventory.reserved_quantity = (
        reserved_after
    )


    item.status = (
        "RELEASED"
    )


    _create_inventory_movement(
        db,

        inventory=
            inventory,

        movement_type=
            "RELEASE",

        quantity=
            item.quantity,

        reserved_before=
            reserved_before,

        reserved_after=
            reserved_after,

        user_id=
            reservation.customer_id,

        reservation=
            reservation,

        reason=
            reason,
    )


# =========================================================
# CU29 - LIBERAR ITEM PENDIENTE
#
# Nunca estuvo físicamente apartado.
# Por lo tanto NO se toca reserved_quantity.
# =========================================================

def _release_pending_item(
    item: ReservationItem,
) -> None:

    if (
        item.status
        !=
        "PENDING"
    ):

        raise RuntimeError(
            "Solo se puede liberar "
            "un item PENDING."
        )


    item.status = (
        "RELEASED"
    )


# =========================================================
# SEED PRINCIPAL
# =========================================================

def seed_reservations(
    db: Session,
) -> None:

    print(
        "🌱 Seed reservas CU28 / CU29..."
    )


    # =====================================================
    # IDEMPOTENCIA
    # =====================================================

    existing_codes = set(
        db.scalars(
            select(
                Reservation
                .reservation_code
            )
        ).all()
    )


    # =====================================================
    # CLIENTES
    # =====================================================

    customers = [
        _get_customer(
            db,
            "cliente01@fashionstore.com",
        ),

        _get_customer(
            db,
            "cliente02@fashionstore.com",
        ),

        _get_customer(
            db,
            "cliente03@fashionstore.com",
        ),

        _get_customer(
            db,
            "cliente04@fashionstore.com",
        ),

        _get_customer(
            db,
            "cliente05@fashionstore.com",
        ),

        _get_customer(
            db,
            "cliente06@fashionstore.com",
        ),
    ]


    # =====================================================
    # ESCENARIOS
    #
    # item_mode:
    #
    # PENDING
    #   Solicitud todavía no apartada.
    #
    # RESERVED
    #   Prenda físicamente apartada.
    #
    # CANCELLED
    #   Primero se reserva y después se libera.
    #
    # EXPIRED
    #   Primero se reserva y después se libera.
    # =====================================================

    scenarios = [

        # =================================================
        # CU29 - ESCENARIO PRINCIPAL
        #
        # Debe mostrar:
        #
        # [ Apartar prendas ]
        # =================================================
        {
            "code":
                "RSV-SEED-0001",

            "customer":
                customers[0],

            "status":
                "PENDING",

            "quantity":
                2,

            "item_mode":
                "PENDING",
        },


        # =================================================
        # RESERVA CONFIRMADA
        # =================================================
        {
            "code":
                "RSV-SEED-0002",

            "customer":
                customers[1],

            "status":
                "CONFIRMED",

            "quantity":
                1,

            "item_mode":
                "RESERVED",
        },


        # =================================================
        # PREPARACIÓN
        # =================================================
        {
            "code":
                "RSV-SEED-0003",

            "customer":
                customers[2],

            "status":
                "PREPARING",

            "quantity":
                2,

            "item_mode":
                "RESERVED",
        },


        # =================================================
        # LISTA
        # =================================================
        {
            "code":
                "RSV-SEED-0004",

            "customer":
                customers[3],

            "status":
                "READY",

            "quantity":
                1,

            "item_mode":
                "RESERVED",
        },


        # =================================================
        # ATENDIDA
        # =================================================
        {
            "code":
                "RSV-SEED-0005",

            "customer":
                customers[4],

            "status":
                "ATTENDED",

            "quantity":
                1,

            "item_mode":
                "RESERVED",
        },


        # =================================================
        # CANCELADA
        #
        # Se reserva y luego se libera.
        # =================================================
        {
            "code":
                "RSV-SEED-0006",

            "customer":
                customers[5],

            "status":
                "CANCELLED",

            "quantity":
                2,

            "item_mode":
                "CANCELLED",
        },


        # =================================================
        # CU29 - PRENDAS YA APARTADAS
        #
        # Reserva sigue PENDING pero item ya RESERVED.
        #
        # Debe mostrar:
        #
        # [ Confirmar reserva ]
        # =================================================
        {
            "code":
                "RSV-SEED-0007",

            "customer":
                customers[0],

            "status":
                "PENDING",

            "quantity":
                1,

            "item_mode":
                "RESERVED",
        },


        # =================================================
        # CU29 - VENCIDA
        #
        # Simula liberación automática.
        # =================================================
        {
            "code":
                "RSV-SEED-0008",

            "customer":
                customers[1],

            "status":
                "EXPIRED",

            "quantity":
                1,

            "item_mode":
                "EXPIRED",
        },
    ]


    # =====================================================
    # 20 RESERVAS PENDIENTES PARA PRUEBAS DE PAGINACION
    # Y FLUJO CU29
    #
    # RSV-CU29-0001 .. RSV-CU29-0010
    #   Reservation = PENDING
    #   ReservationItem = PENDING
    #   -> permite probar "Apartar prendas"
    #
    # RSV-CU29-0011 .. RSV-CU29-0020
    #   Reservation = PENDING
    #   ReservationItem = RESERVED
    #   -> permite probar "Confirmar reserva"
    #
    # Con page_size = 10:
    #   Pagina 1 = 10
    #   Pagina 2 = 10
    # =====================================================

    pending_test_scenarios = []

    for test_index in range(
        1,
        21,
    ):

        pending_test_scenarios.append(
            {
                "code":
                    f"RSV-CU29-{test_index:04d}",

                "customer":
                    customers[
                        (test_index - 1)
                        %
                        len(customers)
                    ],

                "status":
                    "PENDING",

                "quantity":
                    2
                    if test_index % 4 == 0
                    else 1,

                "item_mode":
                    "PENDING"
                    if test_index <= 10
                    else "RESERVED",
            }
        )

    scenarios.extend(
        pending_test_scenarios
    )


    created = (
        0
    )

    skipped = (
        0
    )


    used_inventory_ids:set[int] = set()


    now = (
        datetime.now(
            timezone.utc
        )
    )


    # =====================================================
    # CREAR ESCENARIOS
    # =====================================================

    for (
        index,
        scenario,
    ) in enumerate(
        scenarios,
        start=1,
    ):

        code = (
            scenario[
                "code"
            ]
        )


        # =================================================
        # IDEMPOTENCIA
        # =================================================

        if (
            code
            in
            existing_codes
        ):

            skipped += (
                1
            )

            continue


        # =================================================
        # INVENTARIO
        # =================================================

        inventory = (
            _get_available_inventory(
                db,

                excluded_inventory_ids=
                    used_inventory_ids,

                minimum_available=
                    5,
            )
        )


        used_inventory_ids.add(
            inventory.id
        )


        # =================================================
        # SUCURSAL
        # =================================================

        branch = db.get(
            Branch,

            inventory.branch_id,
        )


        if branch is None:

            raise RuntimeError(
                f"No existe la sucursal "
                f"{inventory.branch_id}."
            )


        # =================================================
        # FECHA DE EXPIRACIÓN
        # =================================================

        if (
            scenario[
                "status"
            ]
            ==
            "EXPIRED"
        ):

            expires_at = (
                now
                -
                timedelta(
                    days=1
                )
            )

        else:

            expires_at = (
                now
                +
                timedelta(
                    days=
                        2
                        +
                        index
                )
            )


        # =================================================
        # RESERVA
        # =================================================

        reservation = Reservation(
            reservation_code=
                code,

            customer_id=
                scenario[
                    "customer"
                ]
                .id,

            branch_id=
                branch.id,

            status=
                scenario[
                    "status"
                ],

            notes=(
                "Reserva generada automáticamente "
                "para pruebas de CU28 y CU29."
            ),

            expires_at=
                expires_at,
        )


        # =================================================
        # FECHAS DE ESTADOS
        # =================================================

        if (
            scenario[
                "status"
            ]
            in
            {
                "PREPARING",
                "READY",
                "ATTENDED",
            }
        ):

            reservation.prepared_at = (
                now
            )


        if (
            scenario[
                "status"
            ]
            ==
            "ATTENDED"
        ):

            reservation.attended_at = (
                now
            )


        if (
            scenario[
                "status"
            ]
            ==
            "CANCELLED"
        ):

            reservation.cancelled_at = (
                now
            )


        db.add(
            reservation
        )


        db.flush()


        # =================================================
        # ITEM
        # =================================================

        item_mode = (
            scenario[
                "item_mode"
            ]
        )


        # =================================================
        # PENDING
        #
        # CU29 todavía NO ejecutado.
        # =================================================

        if (
            item_mode
            ==
            "PENDING"
        ):

            _create_pending_item(
                db,

                reservation=
                    reservation,

                inventory=
                    inventory,

                quantity=
                    scenario[
                        "quantity"
                    ],
            )


        # =================================================
        # RESERVED
        #
        # CU29 ya ejecutado.
        # =================================================

        elif (
            item_mode
            ==
            "RESERVED"
        ):

            _reserve_item(
                db,

                reservation=
                    reservation,

                inventory=
                    inventory,

                quantity=
                    scenario[
                        "quantity"
                    ],
            )


        # =================================================
        # CANCELLED
        #
        # Simula:
        #
        # RESERVE
        #   ↓
        # RELEASE
        # =================================================

        elif (
            item_mode
            ==
            "CANCELLED"
        ):

            item = (
                _reserve_item(
                    db,

                    reservation=
                        reservation,

                    inventory=
                        inventory,

                    quantity=
                        scenario[
                            "quantity"
                        ],
                )
            )


            db.flush()


            _release_reserved_item(
                db,

                reservation=
                    reservation,

                inventory=
                    inventory,

                item=
                    item,

                reason=(
                    "Liberación por cancelación "
                    "de reserva."
                ),
            )


        # =================================================
        # EXPIRED
        #
        # Simula:
        #
        # RESERVE
        #   ↓
        # RELEASE automático
        # =================================================

        elif (
            item_mode
            ==
            "EXPIRED"
        ):

            item = (
                _reserve_item(
                    db,

                    reservation=
                        reservation,

                    inventory=
                        inventory,

                    quantity=
                        scenario[
                            "quantity"
                        ],
                )
            )


            db.flush()


            _release_reserved_item(
                db,

                reservation=
                    reservation,

                inventory=
                    inventory,

                item=
                    item,

                reason=(
                    "Liberación automática "
                    "por vencimiento de reserva."
                ),
            )


        else:

            raise RuntimeError(
                f"item_mode no soportado: "
                f"{item_mode}"
            )


        db.flush()


        created += (
            1
        )


    # =====================================================
    # FINAL
    # =====================================================

    db.flush()


    print(
        "✅ Reservas CU28 / CU29 listas: "
        f"{created} creadas, "
        f"{skipped} ya existentes."
    )


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================

if __name__ == "__main__":

    from app.database.session import (
        SessionLocal,
    )

    from app.database.seeds.seed_customers import (
        seed_customers,
    )


    db = (
        SessionLocal()
    )


    try:

        # =================================================
        # ASEGURAR CLIENTES
        # =================================================

        seed_customers(
            db
        )


        # =================================================
        # CREAR RESERVAS
        # =================================================

        seed_reservations(
            db
        )


        db.commit()


    except Exception:

        db.rollback()

        raise


    finally:

        db.close()
