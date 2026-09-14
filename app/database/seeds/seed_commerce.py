from __future__ import annotations

from sqlalchemy.orm import Session

from app.database.seeds.seed_customers import seed_customers
from app.database.seeds.seed_reservations import seed_reservations
from app.database.seeds.seed_carts import seed_carts
from app.database.seeds.seed_orders import seed_orders
from app.database.seeds.seed_sales import seed_sales
from app.database.seeds.seed_payments import seed_payments
from app.database.seeds.seed_receipts import seed_receipts


def seed_commerce(
    db: Session,
) -> None:

    print()
    print("=" * 70)
    print("FASHIONSTORE - ITERACION 2 / COMERCIO")
    print("=" * 70)

    # =====================================================
    # 1. CLIENTES
    # =====================================================

    seed_customers(
        db
    )

    # =====================================================
    # 2. RESERVAS
    # =====================================================

    seed_reservations(
        db
    )

    # =====================================================
    # 3. CARRITOS
    # =====================================================

    seed_carts(
        db
    )

    # =====================================================
    # 4. COMPRAS DIGITALES
    # =====================================================

    seed_orders(
        db
    )

    # =====================================================
    # 5. VENTAS PRESENCIALES
    # =====================================================

    seed_sales(
        db
    )

    # =====================================================
    # 6. PAGOS
    # =====================================================

    seed_payments(
        db
    )

    # =====================================================
    # 7. COMPROBANTES
    # =====================================================

    seed_receipts(
        db
    )

    db.flush()

    print()
    print("=" * 70)
    print("✅ ITERACION 2 / COMERCIO COMPLETADA")
    print("=" * 70)
    print()


# =========================================================
# EJECUCION DIRECTA
# =========================================================

if __name__ == "__main__":

    from app.database.session import SessionLocal

    db = SessionLocal()

    try:

        seed_commerce(
            db
        )

        db.commit()

    except Exception:

        db.rollback()
        raise

    finally:

        db.close()