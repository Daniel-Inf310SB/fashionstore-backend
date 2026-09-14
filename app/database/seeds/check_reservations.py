from __future__ import annotations

from sqlalchemy import select

from app.database.session import SessionLocal
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.reservation import Reservation
from app.models.reservation_item import ReservationItem
from app.models.user import User


def check_reservations() -> None:
    db = SessionLocal()

    try:
        print()
        print("=" * 70)
        print("VERIFICACION - ITERACION 2 / RESERVAS")
        print("=" * 70)

        reservations = list(
            db.scalars(
                select(Reservation)
                .where(
                    Reservation.reservation_code.like(
                        "RSV-SEED-%"
                    )
                )
                .order_by(
                    Reservation.reservation_code
                )
            ).all()
        )

        if not reservations:
            print("❌ No existen reservas seed.")
            print(
                "Ejecuta primero:"
            )
            print(
                "python -m app.database.seeds.seed_reservations"
            )
            return

        errors = 0

        print(
            f"\nReservas encontradas: {len(reservations)}"
        )

        for reservation in reservations:
            print()
            print("-" * 70)
            print(
                f"{reservation.reservation_code}"
                f" | {reservation.status}"
            )

            customer = db.get(
                User,
                reservation.customer_id,
            )

            if customer is None:
                errors += 1
                print("❌ Cliente inexistente")
            else:
                print(
                    f"Cliente: "
                    f"{customer.first_name} "
                    f"{customer.last_name or ''}"
                )

            items = list(
                db.scalars(
                    select(ReservationItem)
                    .where(
                        ReservationItem.reservation_id
                        == reservation.id
                    )
                    .order_by(
                        ReservationItem.id
                    )
                ).all()
            )

            if not items:
                errors += 1
                print("❌ Reserva sin prendas")
                continue

            print(
                f"Prendas: {len(items)}"
            )

            for item in items:
                inventory = db.scalar(
                    select(Inventory)
                    .where(
                        Inventory.branch_id
                        == reservation.branch_id,
                        Inventory.product_variant_id
                        == item.product_variant_id,
                    )
                )

                if inventory is None:
                    errors += 1
                    print(
                        f"❌ No existe inventario "
                        f"para variante "
                        f"{item.product_variant_id}"
                    )
                    continue

                print(
                    f"  Variante: "
                    f"{item.product_variant_id}"
                )

                print(
                    f"  Cantidad reservada: "
                    f"{item.quantity}"
                )

                print(
                    f"  Estado item: "
                    f"{item.status}"
                )

                print(
                    f"  Stock fisico actual: "
                    f"{inventory.stock_quantity}"
                )

                print(
                    f"  Reservado actual: "
                    f"{inventory.reserved_quantity}"
                )

                print(
                    f"  Disponible actual: "
                    f"{inventory.available_quantity}"
                )

                if (
                    inventory.reserved_quantity
                    > inventory.stock_quantity
                ):
                    errors += 1
                    print(
                        "  ❌ Reservado supera stock fisico"
                    )

                if inventory.reserved_quantity < 0:
                    errors += 1
                    print(
                        "  ❌ reserved_quantity negativo"
                    )

            movements = list(
                db.scalars(
                    select(InventoryMovement)
                    .where(
                        InventoryMovement.reference_type
                        == "RESERVATION",
                        InventoryMovement.reference_id
                        == reservation.id,
                    )
                    .order_by(
                        InventoryMovement.id
                    )
                ).all()
            )

            print(
                f"Movimientos encontrados: "
                f"{len(movements)}"
            )

            if not movements:
                errors += 1
                print(
                    "❌ La reserva no genero "
                    "movimientos de inventario"
                )

            for movement in movements:
                print(
                    f"  {movement.movement_type}"
                    f" | cantidad={movement.quantity}"
                    f" | stock "
                    f"{movement.stock_before}"
                    f" -> {movement.stock_after}"
                    f" | reservado "
                    f"{movement.reserved_before}"
                    f" -> {movement.reserved_after}"
                )

                if movement.movement_type == "RESERVE":
                    expected = (
                        movement.reserved_before
                        + movement.quantity
                    )

                    if (
                        movement.reserved_after
                        != expected
                    ):
                        errors += 1
                        print(
                            "    ❌ RESERVE incoherente"
                        )

                    if (
                        movement.stock_after
                        != movement.stock_before
                    ):
                        errors += 1
                        print(
                            "    ❌ RESERVE modifico "
                            "stock fisico"
                        )

                if movement.movement_type == "RELEASE":
                    expected = (
                        movement.reserved_before
                        - movement.quantity
                    )

                    if (
                        movement.reserved_after
                        != expected
                    ):
                        errors += 1
                        print(
                            "    ❌ RELEASE incoherente"
                        )

                    if (
                        movement.stock_after
                        != movement.stock_before
                    ):
                        errors += 1
                        print(
                            "    ❌ RELEASE modifico "
                            "stock fisico"
                        )

            if reservation.status == "CANCELLED":
                reserve_movements = [
                    movement
                    for movement in movements
                    if movement.movement_type
                    == "RESERVE"
                ]

                release_movements = [
                    movement
                    for movement in movements
                    if movement.movement_type
                    == "RELEASE"
                ]

                if not reserve_movements:
                    errors += 1
                    print(
                        "❌ Reserva cancelada sin RESERVE"
                    )

                if not release_movements:
                    errors += 1
                    print(
                        "❌ Reserva cancelada sin RELEASE"
                    )

                for item in items:
                    if item.status != "RELEASED":
                        errors += 1
                        print(
                            "❌ Item cancelado "
                            "no quedo RELEASED"
                        )

        print()
        print("=" * 70)

        if errors == 0:
            print("✅ TODO CORRECTO")
            print(
                "Reservas, items, inventario y "
                "movimientos son coherentes."
            )
        else:
            print(
                f"❌ SE ENCONTRARON "
                f"{errors} PROBLEMAS"
            )

        print("=" * 70)
        print()

    finally:
        db.close()


if __name__ == "__main__":
    check_reservations()