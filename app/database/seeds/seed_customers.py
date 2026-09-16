from __future__ import annotations

from datetime import date
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User
from app.database.seeds.seed_demo_config import CUSTOMER_COUNT, SEED_PASSWORD

FIRST_NAMES = ["Juan", "María", "Carlos", "Andrea", "Miguel", "Lucía", "Diego", "Valeria", "José", "Camila", "Luis", "Daniela", "Fernando", "Paola", "Marco", "Gabriela", "Jorge", "Natalia", "Sergio", "Alejandra"]
LAST_NAMES = ["Pérez", "Gutiérrez", "Fernández", "Rojas", "Vargas", "Mendoza", "Suárez", "Flores", "Torrez", "Salazar", "Romero", "Cabrera", "Ortiz", "Aguilar", "Rivera", "Castro", "Morales", "López", "Guzmán", "Vega"]
CITIES = ["Santa Cruz de la Sierra", "La Paz", "Cochabamba", "Sucre", "Oruro", "Potosí", "Tarija", "Trinidad", "Cobija"]


def seed_customers(db: Session) -> None:
    print(f"🌱 Seed clientes: {CUSTOMER_COUNT} clientes...")
    role = db.scalar(select(Role).where(Role.name == "CLIENTE"))
    if role is None:
        raise RuntimeError("No existe el rol CLIENTE. Ejecuta seed_auth primero.")

    created = updated = 0
    for i in range(1, CUSTOMER_COUNT + 1):
        email = f"cliente{i:02d}@fashionstore.com"
        user = db.scalar(select(User).where(User.email == email))
        first = FIRST_NAMES[(i - 1) % len(FIRST_NAMES)]
        last = LAST_NAMES[(i * 3 - 1) % len(LAST_NAMES)]
        payload = dict(username=f"cliente{i:02d}", first_name=first, last_name=last, phone=f"71{i:06d}"[-8:], document_number=f"CLI26{i:05d}", address=CITIES[(i - 1) % len(CITIES)], date_of_birth=date(1988 + (i % 17), ((i - 1) % 12) + 1, ((i * 2 - 1) % 27) + 1), role_id=role.id, is_active=True, is_verified=True, profile_completed=True)
        if user is None:
            user = User(email=email, password_hash=hash_password(SEED_PASSWORD), **payload)
            db.add(user)
            created += 1
        else:
            for key, value in payload.items(): setattr(user, key, value)
            updated += 1
    db.flush()
    print(f"✅ Clientes listos: {created} creados, {updated} actualizados.")


if __name__ == "__main__":
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        seed_customers(db); db.commit()
    except Exception:
        db.rollback(); raise
    finally:
        db.close()
