from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.database.seeds.seed_locations import BRANCHES
from app.database.seeds.seed_staffing import build_staff_plan


def seed_users(db: Session) -> None:
    print("🌱 Seed empleados: personal completo por sucursal...")

    roles = {
        role.name: role
        for role in db.scalars(
            select(Role).where(Role.name.in_(["ENCARGADO_SUCURSAL", "CAJERO"]))
        ).all()
    }
    if set(roles) != {"ENCARGADO_SUCURSAL", "CAJERO"}:
        raise RuntimeError("Faltan roles ENCARGADO_SUCURSAL o CAJERO. Ejecuta seed_auth primero.")

    plan = build_staff_plan(BRANCHES)
    created = 0
    updated = 0

    for item in plan:
        user = db.scalar(select(User).where(User.email == item["email"]))
        payload = {
            "username": item["username"],
            "first_name": item["first_name"],
            "last_name": item["last_name"],
            "phone": item["phone"],
            "document_number": item["document_number"],
            "address": item["city"],
            "date_of_birth": item["date_of_birth"],
            "role_id": roles[item["role"]].id,
            "is_active": True,
            "is_verified": True,
            "profile_completed": True,
        }

        if user is None:
            user = User(
                email=item["email"],
                password_hash=hash_password(item["password"]),
                **payload,
            )
            db.add(user)
            created += 1
        else:
            for key, value in payload.items():
                setattr(user, key, value)
            if not user.password_hash:
                user.password_hash = hash_password(item["password"])
            updated += 1

    db.flush()

    managers = sum(1 for x in plan if x["role"] == "ENCARGADO_SUCURSAL")
    cashiers = sum(1 for x in plan if x["role"] == "CAJERO")
    print(
        f"✅ Empleados listos: {created} creados, {updated} actualizados | "
        f"encargados={managers}, cajeros={cashiers}."
    )


if __name__ == "__main__":
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        seed_users(db)
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
