from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User


CUSTOMERS = [
    {
        "username": "cliente01",
        "first_name": "Juan",
        "last_name": "Pérez",
        "email": "cliente01@fashionstore.com",
        "password": "Cliente123*",
        "phone": "71000001",
        "document_number": "CLI100001",
        "address": "Santa Cruz de la Sierra",
        "date_of_birth": date(1998, 4, 12),
    },
    {
        "username": "cliente02",
        "first_name": "María",
        "last_name": "Gutiérrez",
        "email": "cliente02@fashionstore.com",
        "password": "Cliente123*",
        "phone": "71000002",
        "document_number": "CLI100002",
        "address": "La Paz",
        "date_of_birth": date(1997, 8, 21),
    },
    {
        "username": "cliente03",
        "first_name": "Carlos",
        "last_name": "Fernández",
        "email": "cliente03@fashionstore.com",
        "password": "Cliente123*",
        "phone": "71000003",
        "document_number": "CLI100003",
        "address": "Cochabamba",
        "date_of_birth": date(2000, 2, 10),
    },
    {
        "username": "cliente04",
        "first_name": "Andrea",
        "last_name": "Rojas",
        "email": "cliente04@fashionstore.com",
        "password": "Cliente123*",
        "phone": "71000004",
        "document_number": "CLI100004",
        "address": "Sucre",
        "date_of_birth": date(1999, 11, 5),
    },
    {
        "username": "cliente05",
        "first_name": "Miguel",
        "last_name": "Vargas",
        "email": "cliente05@fashionstore.com",
        "password": "Cliente123*",
        "phone": "71000005",
        "document_number": "CLI100005",
        "address": "Oruro",
        "date_of_birth": date(1996, 6, 18),
    },
    {
        "username": "cliente06",
        "first_name": "Lucía",
        "last_name": "Mendoza",
        "email": "cliente06@fashionstore.com",
        "password": "Cliente123*",
        "phone": "71000006",
        "document_number": "CLI100006",
        "address": "Tarija",
        "date_of_birth": date(2001, 1, 25),
    },
]


def seed_customers(
    db: Session,
) -> None:

    print(
        "🌱 Seed clientes..."
    )

    customer_role = db.scalar(
        select(Role)
        .where(
            Role.name == "CLIENTE"
        )
    )

    if customer_role is None:
        raise RuntimeError(
            "No existe el rol CLIENTE. "
            "Ejecuta seed_auth primero."
        )

    created = 0
    existing = 0

    for data in CUSTOMERS:

        customer = db.scalar(
            select(User)
            .where(
                User.email == data["email"]
            )
        )

        if customer is not None:
            existing += 1
            continue

        customer = User(
            username=data["username"],
            first_name=data["first_name"],
            last_name=data["last_name"],
            email=data["email"],
            phone=data["phone"],
            document_number=data["document_number"],
            address=data["address"],
            date_of_birth=data["date_of_birth"],
            password_hash=hash_password(
                data["password"]
            ),
            role_id=customer_role.id,
            is_active=True,
            is_verified=True,
            profile_completed=True,
        )

        db.add(
            customer
        )

        created += 1

    db.flush()

    print(
        "✅ Clientes listos: "
        f"{created} creados, "
        f"{existing} ya existentes."
    )
if __name__ == "__main__":
    from app.database.session import SessionLocal

    db = SessionLocal()

    try:
        seed_customers(db)
        db.commit()

    except Exception:
        db.rollback()
        raise

    finally:
        db.close()