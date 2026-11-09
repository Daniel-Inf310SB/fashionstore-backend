"""Administradores tenant, superadmin y empleados demo."""
import os
from dotenv import load_dotenv
load_dotenv()
from sqlalchemy import select
from app.core.security import hash_password
from app.models.user import User
from app.models.platform_admin import PlatformAdmin

# No incluimos contraseñas fijas en el repositorio: requieren variables de entorno.
def _password(key):
    value = os.environ.get(key)
    if not value or len(value) < 12:
        raise RuntimeError(f"Configura {key} con una contraseña de al menos 12 caracteres (solo entorno de pruebas)")
    return value

def _ensure_user(db, *, email, username, name, surname, tenant_id, role, password):
    user = db.scalar(select(User).where(User.email == email))
    if user is None:
        existing = db.scalar(select(User).where(User.username == username))
        if existing:
            raise RuntimeError(f"Username ocupado: {username}")
        user = User(email=email, username=username, first_name=name, last_name=surname,
                    tenant_id=tenant_id, role_id=role.id, password_hash=hash_password(password),
                    is_active=True, is_verified=True, profile_completed=True)
        db.add(user)
        db.flush()
    elif user.tenant_id != tenant_id or user.role_id != role.id:
        raise RuntimeError(f"Usuario preexistente con tenant o rol distinto: {email}")
    return user

def seed_users(db, tenant_ids, roles, branches):
    admin_password = _password("SEED_TENANT_ADMIN_PASSWORD")
    staff_password = _password("SEED_STAFF_PASSWORD")
    super_password = _password("SEED_SUPER_ADMIN_PASSWORD")
    superuser = _ensure_user(db, email="superadmin@example.com", username="fs_superadmin", name="Super", surname="Administrador",
                             tenant_id=None, role=roles["SUPER_ADMIN"], password=super_password)
    record = db.scalar(select(PlatformAdmin).where(PlatformAdmin.user_id == superuser.id))
    if record is None:
        db.add(PlatformAdmin(user_id=superuser.id, is_active=True))
    elif not record.is_active:
        raise RuntimeError("SUPER_ADMIN previamente desactivado: requiere activación manual")
    admins = [
        ("fashionstore", "admin@fashionstore.com", "admin_fashionstore", "Administrador", "FashionStore"),
        ("urban-style-demo", "admin@example.com", "admin_urbanstyle", "Administrador", "UrbanStyle"),
        ("technova-store", "admin@technova.example.com", "admin_technova", "Administrador", "TechNova"),
    ]
    for slug,email,username,first,last in admins:
        _ensure_user(db, email=email, username=username, name=first, surname=last, tenant_id=tenant_ids[slug],
                     role=roles["TENANT_ADMIN"], password=admin_password)
    users_by_branch = {}
    for branch in branches:
        code = next((prefix for slug, prefix in (("fashionstore", "fs"), ("urban-style-demo", "us"), ("technova-store", "tn")) if tenant_ids[slug] == branch.tenant_id), None)
        if code is None: raise RuntimeError("Sucursal con tenant desconocido")
        members = []
        for index, role in enumerate(["ENCARGADO_SUCURSAL", "CAJERO", "CAJERO"], 1):
            username = f"{code}_{'enc' if index == 1 else 'caj'}_{branch.id}_{index}"
            email = username + "@example.com"
            user = _ensure_user(db, email=email, username=username, name="Encargado" if index == 1 else "Cajero", surname=f"Sucursal {branch.id}",
                                tenant_id=branch.tenant_id, role=roles[role], password=staff_password)
            members.append(user)
        users_by_branch[branch.id] = members
    db.flush()
    return users_by_branch
