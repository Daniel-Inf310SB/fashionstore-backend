"""Alinea planes existentes al examen 2 sin tocar suscripciones ni precios.

Desde la raíz del backend:
  python -m app.database.seeds.sync_exam2_plans          # vista previa, no escribe
  python -m app.database.seeds.sync_exam2_plans --apply  # confirma cambios
"""
from __future__ import annotations

import argparse
from sqlalchemy import select
from app.database.session import SessionLocal
from app.models.subscription_plan import SubscriptionPlan

# Mismo mapa que utiliza el seed, sin alterar precios ni máximos de personal.
EXPECTED = {
    "basico": {"max_branches": 2, "features": ["catalog", "inventory", "sales", "reservations", "offline_sync", "advanced_reports"]},
    "profesional": {"max_branches": 10, "features": ["catalog", "inventory", "sales", "reservations", "offline_sync", "advanced_reports", "ai_reports"]},
}


def main() -> None:
    parser = argparse.ArgumentParser(description="Actualizar límites y funciones de planes académicos")
    parser.add_argument("--apply", action="store_true", help="Confirmar actualización de los planes existentes")
    args = parser.parse_args()
    import app.models  # noqa: F401  - registra modelos ORM
    with SessionLocal() as db:
        try:
            for code, desired in EXPECTED.items():
                plan = db.scalar(select(SubscriptionPlan).where(SubscriptionPlan.code == code).with_for_update())
                if plan is None:
                    print(f"{code}: NO EXISTE. Crea primero los planes desde el panel o el seed.")
                    continue
                updates = {}
                for field, wanted in desired.items():
                    existing = getattr(plan, field)
                    if existing != wanted:
                        updates[field] = (existing, wanted)
                if not updates:
                    print(f"{code}: correcto, sin cambios")
                    continue
                for field, (before, after) in updates.items():
                    print(f"{code}.{field}: {before!r} -> {after!r}")
                    if args.apply:
                        setattr(plan, field, after)
            if args.apply:
                db.commit()
                print("Actualización confirmada. Suscripciones, pagos, precios y personal no modificados.")
            else:
                db.rollback()
                print("VISTA PREVIA: sin escrituras. Usa --apply después de revisar.")
        except Exception:
            db.rollback()
            raise


if __name__ == "__main__":
    main()
