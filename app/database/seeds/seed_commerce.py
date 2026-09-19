from __future__ import annotations

from sqlalchemy.orm import Session
from app.database.seeds.seed_demo_commerce import seed_demo_commerce


def seed_commerce(db: Session) -> None:
    """Orquestador de Iteración 2 con dataset comercial 2026 realista y coherente."""
    seed_demo_commerce(db)


if __name__ == "__main__":
    from app.database.session import SessionLocal
    db = SessionLocal()
    try:
        seed_commerce(db); db.commit()
    except Exception:
        db.rollback(); raise
    finally:
        db.close()
