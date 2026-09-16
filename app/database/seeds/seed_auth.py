from sqlalchemy import select

from app.core.security import hash_password
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User


# =========================================================
# ROLES
# =========================================================

ROLES = [
    {
        "name": "ADMINISTRADOR",
        "description": "Administra la plataforma FashionStore.",
    },
    {
        "name": "ENCARGADO_SUCURSAL",
        "description": "Gestiona operaciones de una sucursal.",
    },
    {
        "name": "CAJERO",
        "description": "Gestiona ventas y pagos presenciales.",
    },
    {
        "name": "CLIENTE",
        "description": "Cliente de la plataforma FashionStore.",
    },
    {
        "name": "PROVEEDOR",
        "description": "Proveedor de productos de FashionStore.",
    },
]


# =========================================================
# PERMISOS
# =========================================================

PERMISSIONS = [
    {
        "code": "users.manage",
        "name": "Gestionar usuarios",
    },
    {
        "code": "roles.manage",
        "name": "Gestionar roles",
    },
    {
        "code": "branches.manage",
        "name": "Gestionar sucursales",
    },
    {
        "code": "branch_staff.view",
        "name": "Consultar personal de sucursal",
    },
    {
        "code": "branch_staff.manage",
        "name": "Gestionar personal de sucursal",
    },
    {
        "code": "products.manage",
        "name": "Gestionar productos",
    },
    {
        "code": "products.view",
        "name": "Consultar productos",
    },
    {
        "code": "suppliers.manage",
        "name": "Gestionar proveedores",
    },
    {
        "code": "inventory.manage",
        "name": "Gestionar inventario",
    },
    {
        "code": "inventory.view",
        "name": "Consultar inventario",
    },
    {
        "code": "inventory.movements.view",
        "name": "Consultar movimientos de inventario",
    },
    {
        "code": "inventory.movements.manage",
        "name": "Registrar movimientos manuales de inventario",
    },
    {
        "code": "reservations.manage",
        "name": "Gestionar reservas",
    },
    {
        "code": "reservations.view",
        "name": "Consultar reservas",
    },
    {
        "code": "cart.manage",
        "name": "Gestionar carrito",
    },
    {
        "code": "purchases.create",
        "name": "Realizar compras",
    },
    {
        "code": "purchases.view",
        "name": "Consultar compras",
    },
    {
        "code": "sales.create",
        "name": "Registrar ventas",
    },
    {
        "code": "sales.view",
        "name": "Consultar ventas",
    },
    {
        "code": "sales.manage",
        "name": "Gestionar ventas presenciales",
    },
    {
        "code": "payments.process",
        "name": "Procesar pagos",
    },
    {
        "code": "payments.view",
        "name": "Consultar pagos electrónicos",
    },
    {
        "code": "payments.manage",
        "name": "Gestionar pagos electrónicos",
    },
    {
        "code": "receipts.create",
        "name": "Emitir comprobantes",
    },
    {
        "code": "virtual_fitting.use",
        "name": "Utilizar vestidor virtual",
    },
    {
        "code": "ai.recommendations",
        "name": "Obtener recomendaciones IA",
    },
    {
        "code": "ai.assistant",
        "name": "Utilizar asistente IA",
    },
    {
        "code": "reports.view",
        "name": "Consultar reportes",
    },
    {
        "code": "dashboard.view",
        "name": "Consultar dashboard",
    },
]


# =========================================================
# PERMISOS POR ROL
# =========================================================

ROLE_PERMISSIONS = {
    "ADMINISTRADOR": [
        "users.manage",
        "roles.manage",
        "branches.manage",
        "branch_staff.view",
        "branch_staff.manage",
        "products.manage",
        "products.view",
        "suppliers.manage",
        "inventory.manage",
        "inventory.view",
        "inventory.movements.view",
        "inventory.movements.manage",
        "reservations.manage",
        "reservations.view",
        "cart.manage",
        "purchases.view",
        "sales.view",
        "sales.manage",
        "payments.view",
        "payments.manage",
        "reports.view",
        "dashboard.view",
    ],

    "ENCARGADO_SUCURSAL": [
        "branch_staff.view",
        "products.view",
        "inventory.manage",
        "inventory.view",
        "inventory.movements.view",
        "inventory.movements.manage",
        "reservations.manage",
        "reservations.view",
        "sales.view",
        "sales.manage",
    ],

    "CAJERO": [
        "products.view",
        "inventory.view",
        "sales.create",
        "sales.view",
        "payments.process",
        "receipts.create",
    ],

    "CLIENTE": [
        "products.view",
        "reservations.manage",
        "cart.manage",
        "purchases.create",
        "purchases.view",
        "payments.process",
        "virtual_fitting.use",
        "ai.recommendations",
        "ai.assistant",
    ],

    "PROVEEDOR": [
        "products.view",
    ],
}


# =========================================================
# CREAR ROLES
# =========================================================

def seed_roles(db):

    print("Creando roles...")

    for role_data in ROLES:

        role = db.scalar(
            select(Role).where(
                Role.name == role_data["name"]
            )
        )

        if role:
            print(
                f"  - {role_data['name']} ya existe"
            )
            continue

        role = Role(
            name=role_data["name"],
            description=role_data["description"],
            is_active=True,
        )

        db.add(role)

        print(
            f"  + Rol creado: {role_data['name']}"
        )

    db.commit()


# =========================================================
# CREAR PERMISOS
# =========================================================

def seed_permissions(db):

    print("Creando permisos...")

    for permission_data in PERMISSIONS:

        permission = db.scalar(
            select(Permission).where(
                Permission.code
                == permission_data["code"]
            )
        )

        if permission:
            print(
                f"  - {permission_data['code']} ya existe"
            )
            continue

        permission = Permission(
            code=permission_data["code"],
            name=permission_data["name"],
            is_active=True,
        )

        db.add(permission)

        print(
            f"  + Permiso creado: "
            f"{permission_data['code']}"
        )

    db.commit()


# =========================================================
# ASIGNAR PERMISOS
# =========================================================

def seed_role_permissions(db):

    print("Asignando permisos...")

    for role_name, permission_codes in ROLE_PERMISSIONS.items():

        role = db.scalar(
            select(Role).where(
                Role.name == role_name
            )
        )

        if not role:
            print(
                f"  ! Rol no encontrado: {role_name}"
            )
            continue

        permissions = db.scalars(
            select(Permission).where(
                Permission.code.in_(
                    permission_codes
                )
            )
        ).all()

        role.permissions = permissions

        print(
            f"  + Permisos asignados a {role_name}"
        )

    db.commit()


# =========================================================
# ADMINISTRADOR
# =========================================================

def seed_admin(db):

    print("Creando administrador...")

    admin_role = db.scalar(
        select(Role).where(
            Role.name == "ADMINISTRADOR"
        )
    )

    if not admin_role:
        raise RuntimeError(
            "No existe el rol ADMINISTRADOR"
        )

    admin_email = "admin@fashionstore.com"

    admin = db.scalar(
        select(User).where(
            User.email == admin_email
        )
    )

    if admin:
        print(
            f"  - {admin_email} ya existe"
        )
        return

    admin = User(
        username="admin",
        first_name="Administrador",
        last_name="FashionStore",
        email=admin_email,
        password_hash=hash_password(
            "Admin123*"
        ),
        role_id=admin_role.id,
        is_active=True,
        is_verified=True,
        profile_completed=True,
    )

    db.add(admin)
    db.commit()

    print(
        f"  + Administrador creado: {admin_email}"
    )


# =========================================================
# SEED AUTH
# =========================================================

def seed_auth(db):

    print("")
    print("======================================")
    print("              SEED AUTH")
    print("======================================")
    print("")

    seed_roles(db)

    seed_permissions(db)

    seed_role_permissions(db)

    seed_admin(db)

    print("")
    print("  ✓ Seed de autenticación completado")
    print("")
# =========================================================
# MAIN
# =========================================================

def main():

    from app.database.session import SessionLocal

    db = SessionLocal()

    try:
        seed_auth(db)

    except Exception as exc:

        db.rollback()

        print("")
        print("======================================")
        print("       ERROR EN SEED AUTH")
        print("======================================")
        print("")
        print(exc)
        print("")

        raise

    finally:
        db.close()


# =========================================================
# EJECUCIÓN DIRECTA
# =========================================================

if __name__ == "__main__":
    main()