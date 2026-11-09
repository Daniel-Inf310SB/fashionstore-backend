"""Asignaciones exclusivas por sucursal y tenant."""
from sqlalchemy import select
from app.models.employee_branch import EmployeeBranch

def seed_staffing(db, branches, users_by_branch):
    count = 0
    for branch in branches:
        for user in users_by_branch[branch.id]:
            if user.tenant_id != branch.tenant_id:
                raise RuntimeError("Cruce de tenants detectado al asignar personal")
            current = db.scalar(select(EmployeeBranch).where(EmployeeBranch.user_id == user.id, EmployeeBranch.is_active.is_(True)))
            if current:
                if current.branch_id != branch.id:
                    raise RuntimeError(f"Empleado {user.id} ya tiene otra sucursal activa")
                continue
            db.add(EmployeeBranch(user_id=user.id, branch_id=branch.id, is_active=True))
            count += 1
    db.flush()
    return count
