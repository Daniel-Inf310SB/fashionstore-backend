from __future__ import annotations

from collections import Counter, defaultdict
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.city import City
from app.models.collection import Collection
from app.models.employee_branch import EmployeeBranch
from app.models.order import Order
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.promotion import Promotion
from app.models.reservation import Reservation
from app.models.role import Role
from app.models.sale import Sale
from app.models.season import Season
from app.models.shopping_cart import ShoppingCart
from app.models.user import User


def _count(db: Session, model) -> int:
    return int(db.scalar(select(func.count()).select_from(model)) or 0)


def check_demo_dataset(db: Session) -> None:
    roles = {r.id: r.name for r in db.scalars(select(Role)).all()}
    users = list(db.scalars(select(User)).all())
    role_counts = Counter(roles.get(u.role_id, "UNKNOWN") for u in users)

    sales = list(db.scalars(select(Sale)).all())
    orders = list(db.scalars(select(Order)).all())
    reservations = list(db.scalars(select(Reservation)).all())
    carts = list(db.scalars(select(ShoppingCart)).all())

    assignments = list(
        db.execute(
            select(EmployeeBranch, User)
            .join(User, User.id == EmployeeBranch.user_id)
            .where(EmployeeBranch.is_active.is_(True))
        ).all()
    )
    staff_by_branch = defaultdict(Counter)
    for assignment, user in assignments:
        staff_by_branch[assignment.branch_id][roles.get(user.role_id, "UNKNOWN")] += 1

    branch_issues = []
    for branch in db.scalars(select(Branch).where(Branch.is_active.is_(True))).all():
        counts = staff_by_branch[branch.id]
        if counts["ENCARGADO_SUCURSAL"] != 1 or not (1 <= counts["CAJERO"] <= 2):
            branch_issues.append((branch.name, dict(counts)))

    active_promos = int(
        db.scalar(
            select(func.count()).select_from(Promotion).where(Promotion.is_active.is_(True))
        ) or 0
    )

    print("\n" + "=" * 72)
    print("FASHIONSTORE - VERIFICACIÓN DATASET DEMO")
    print("=" * 72)
    print(f"Ciudades: {_count(db, City)}")
    print(f"Sucursales: {_count(db, Branch)}")
    print(f"Usuarios por rol: {dict(role_counts)}")
    print(f"Productos: {_count(db, Product)}")
    print(f"Variantes: {_count(db, ProductVariant)}")
    print(f"Temporadas: {_count(db, Season)}")
    print(f"Colecciones: {_count(db, Collection)}")
    print(f"Promociones: {_count(db, Promotion)} | activas={active_promos}")
    print(f"Ventas: {len(sales)} | estados={dict(Counter(x.status for x in sales))}")
    print(f"Órdenes: {len(orders)} | estados={dict(Counter(x.status for x in orders))}")
    print(f"Reservas: {len(reservations)} | estados={dict(Counter(x.status for x in reservations))}")
    print(f"Carritos: {len(carts)} | estados={dict(Counter(x.status for x in carts))}")
    print(f"Sucursales con staffing inválido: {branch_issues or 'ninguna'}")
    print("=" * 72 + "\n")


if __name__ == "__main__":
    from app.database.session import SessionLocal

    db = SessionLocal()
    try:
        check_demo_dataset(db)
    finally:
        db.close()
