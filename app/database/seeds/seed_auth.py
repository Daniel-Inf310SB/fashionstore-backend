"""Bloque 2: roles y permisos idempotentes. Sin commits internos."""
from sqlalchemy import select
from app.models.role import Role
from app.models.permission import Permission
from app.database.seeds.seed_reference_data import ROLES, PERMISSIONS, ROLE_PERMISSIONS

def seed_auth(db):
    role_defs = {r["name"]: r["description"] for r in ROLES}
    role_defs.pop("ADMINISTRADOR", None)
    role_defs["TENANT_ADMIN"] = "Administra exclusivamente su empresa"
    role_defs["SUPER_ADMIN"] = "Identidad global; permisos gestionados en platform_admins"
    roles = {}
    for name, description in role_defs.items():
        role = db.scalar(select(Role).where(Role.name == name))
        if role is None:
            role = Role(name=name, description=description, is_active=True)
            db.add(role)
            db.flush()
        else:
            role.is_active = True
        roles[name] = role
    perms = {}
    for spec in PERMISSIONS:
        perm = db.scalar(select(Permission).where(Permission.code == spec["code"]))
        if perm is None:
            perm = Permission(code=spec["code"], name=spec["name"], is_active=True)
            db.add(perm)
            db.flush()
        perms[spec["code"]] = perm
    mappings = dict(ROLE_PERMISSIONS)
    mappings["TENANT_ADMIN"] = mappings.pop("ADMINISTRADOR")
    mappings["SUPER_ADMIN"] = []  # No hereda permisos de ventas ni inventario
    for name, codes in mappings.items():
        if name not in roles:
            raise ValueError(f"Rol inexistente: {name}")
        missing = set(codes) - set(perms)
        if missing:
            raise ValueError(f"Permisos desconocidos para {name}: {missing}")
        roles[name].permissions = [perms[code] for code in codes]
    db.flush()
    return roles
