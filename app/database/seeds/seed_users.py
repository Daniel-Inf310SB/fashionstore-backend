from datetime import date

from sqlalchemy import or_, select

from app.core.security import hash_password
from app.models.role import Role
from app.models.user import User


# =========================================================
# EMPLEADOS
# =========================================================

EMPLOYEES = [

    # =====================================================
    # SANTA CRUZ
    # =====================================================

    {
        "username": "encargado.sc",
        "first_name": "Carlos",
        "last_name": "Rojas",
        "email": "encargado.sc@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000001",
        "document_number": "FS100001",
        "date_of_birth": date(1990, 5, 12),
        "role": "ENCARGADO_SUCURSAL",
    },
    {
        "username": "cajero.sc1",
        "first_name": "María",
        "last_name": "Flores",
        "email": "cajero.sc1@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000002",
        "document_number": "FS100002",
        "date_of_birth": date(1995, 8, 20),
        "role": "CAJERO",
    },
    {
        "username": "cajero.sc2",
        "first_name": "José",
        "last_name": "Mendoza",
        "email": "cajero.sc2@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000003",
        "document_number": "FS100003",
        "date_of_birth": date(1994, 4, 15),
        "role": "CAJERO",
    },


    # =====================================================
    # LA PAZ
    # =====================================================

    {
        "username": "encargado.lp",
        "first_name": "Luis",
        "last_name": "Mamani",
        "email": "encargado.lp@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000004",
        "document_number": "FS100004",
        "date_of_birth": date(1989, 3, 14),
        "role": "ENCARGADO_SUCURSAL",
    },
    {
        "username": "cajero.lp1",
        "first_name": "Andrea",
        "last_name": "Quispe",
        "email": "cajero.lp1@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000005",
        "document_number": "FS100005",
        "date_of_birth": date(1998, 10, 2),
        "role": "CAJERO",
    },
    {
        "username": "cajero.lp2",
        "first_name": "Daniel",
        "last_name": "Condori",
        "email": "cajero.lp2@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000006",
        "document_number": "FS100006",
        "date_of_birth": date(1996, 7, 18),
        "role": "CAJERO",
    },


    # =====================================================
    # COCHABAMBA
    # =====================================================

    {
        "username": "encargado.cbba",
        "first_name": "Diego",
        "last_name": "Vargas",
        "email": "encargado.cbba@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000007",
        "document_number": "FS100007",
        "date_of_birth": date(1992, 6, 17),
        "role": "ENCARGADO_SUCURSAL",
    },
    {
        "username": "cajero.cbba1",
        "first_name": "Fernanda",
        "last_name": "López",
        "email": "cajero.cbba1@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000008",
        "document_number": "FS100008",
        "date_of_birth": date(1997, 1, 25),
        "role": "CAJERO",
    },
    {
        "username": "cajero.cbba2",
        "first_name": "Miguel",
        "last_name": "Camacho",
        "email": "cajero.cbba2@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000009",
        "document_number": "FS100009",
        "date_of_birth": date(1995, 11, 9),
        "role": "CAJERO",
    },


    # =====================================================
    # CHUQUISACA
    # =====================================================

    {
        "username": "encargado.ch",
        "first_name": "Ricardo",
        "last_name": "Torrez",
        "email": "encargado.ch@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000010",
        "document_number": "FS100010",
        "date_of_birth": date(1991, 2, 11),
        "role": "ENCARGADO_SUCURSAL",
    },
    {
        "username": "cajero.ch1",
        "first_name": "Gabriela",
        "last_name": "Sánchez",
        "email": "cajero.ch1@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000011",
        "document_number": "FS100011",
        "date_of_birth": date(1997, 9, 4),
        "role": "CAJERO",
    },
    {
        "username": "cajero.ch2",
        "first_name": "Kevin",
        "last_name": "Molina",
        "email": "cajero.ch2@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000012",
        "document_number": "FS100012",
        "date_of_birth": date(1999, 12, 7),
        "role": "CAJERO",
    },


    # =====================================================
    # ORURO
    # =====================================================

    {
        "username": "encargado.or",
        "first_name": "Ramiro",
        "last_name": "Choque",
        "email": "encargado.or@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000013",
        "document_number": "FS100013",
        "date_of_birth": date(1988, 8, 30),
        "role": "ENCARGADO_SUCURSAL",
    },
    {
        "username": "cajero.or1",
        "first_name": "Paola",
        "last_name": "Huanca",
        "email": "cajero.or1@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000014",
        "document_number": "FS100014",
        "date_of_birth": date(1996, 5, 21),
        "role": "CAJERO",
    },
    {
        "username": "cajero.or2",
        "first_name": "Marco",
        "last_name": "Villca",
        "email": "cajero.or2@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000015",
        "document_number": "FS100015",
        "date_of_birth": date(1993, 7, 13),
        "role": "CAJERO",
    },


    # =====================================================
    # POTOSÍ
    # =====================================================

    {
        "username": "encargado.pt",
        "first_name": "Óscar",
        "last_name": "Colque",
        "email": "encargado.pt@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000016",
        "document_number": "FS100016",
        "date_of_birth": date(1990, 10, 19),
        "role": "ENCARGADO_SUCURSAL",
    },
    {
        "username": "cajero.pt1",
        "first_name": "Lucía",
        "last_name": "Cruz",
        "email": "cajero.pt1@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000017",
        "document_number": "FS100017",
        "date_of_birth": date(1998, 3, 8),
        "role": "CAJERO",
    },
    {
        "username": "cajero.pt2",
        "first_name": "Héctor",
        "last_name": "Arias",
        "email": "cajero.pt2@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000018",
        "document_number": "FS100018",
        "date_of_birth": date(1995, 6, 22),
        "role": "CAJERO",
    },


    # =====================================================
    # TARIJA
    # =====================================================

    {
        "username": "encargado.tj",
        "first_name": "Rodrigo",
        "last_name": "Castillo",
        "email": "encargado.tj@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000019",
        "document_number": "FS100019",
        "date_of_birth": date(1990, 1, 13),
        "role": "ENCARGADO_SUCURSAL",
    },
    {
        "username": "cajero.tj1",
        "first_name": "Natalia",
        "last_name": "Romero",
        "email": "cajero.tj1@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000020",
        "document_number": "FS100020",
        "date_of_birth": date(1997, 4, 26),
        "role": "CAJERO",
    },
    {
        "username": "cajero.tj2",
        "first_name": "Javier",
        "last_name": "Cárdenas",
        "email": "cajero.tj2@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000021",
        "document_number": "FS100021",
        "date_of_birth": date(1994, 9, 15),
        "role": "CAJERO",
    },


    # =====================================================
    # BENI
    # =====================================================

    {
        "username": "encargado.be",
        "first_name": "Mauricio",
        "last_name": "Suárez",
        "email": "encargado.be@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000022",
        "document_number": "FS100022",
        "date_of_birth": date(1991, 11, 5),
        "role": "ENCARGADO_SUCURSAL",
    },
    {
        "username": "cajero.be1",
        "first_name": "Carla",
        "last_name": "Ribera",
        "email": "cajero.be1@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000023",
        "document_number": "FS100023",
        "date_of_birth": date(1998, 6, 2),
        "role": "CAJERO",
    },
    {
        "username": "cajero.be2",
        "first_name": "Álvaro",
        "last_name": "Méndez",
        "email": "cajero.be2@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000024",
        "document_number": "FS100024",
        "date_of_birth": date(1993, 3, 12),
        "role": "CAJERO",
    },


    # =====================================================
    # PANDO
    # =====================================================

    {
        "username": "encargado.pd",
        "first_name": "Víctor",
        "last_name": "Salazar",
        "email": "encargado.pd@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000025",
        "document_number": "FS100025",
        "date_of_birth": date(1989, 12, 3),
        "role": "ENCARGADO_SUCURSAL",
    },
    {
        "username": "cajero.pd1",
        "first_name": "Daniela",
        "last_name": "Vaca",
        "email": "cajero.pd1@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000026",
        "document_number": "FS100026",
        "date_of_birth": date(1999, 2, 17),
        "role": "CAJERO",
    },
    {
        "username": "cajero.pd2",
        "first_name": "Fernando",
        "last_name": "Paz",
        "email": "cajero.pd2@fashionstore.com",
        "password": "Empleado123*",
        "phone": "70000027",
        "document_number": "FS100027",
        "date_of_birth": date(1995, 7, 28),
        "role": "CAJERO",
    },
]


# =========================================================
# BUSCAR USUARIO EXISTENTE DEL SEED
# =========================================================

def find_existing_seed_user(
    db,
    username: str,
    email: str,
    document_number: str,
):

    matches = db.scalars(
        select(User).where(
            or_(
                User.username == username,
                User.email == email,
                User.document_number == document_number,
            )
        )
    ).all()

    # Eliminar repetidos por ID.
    # Un mismo usuario puede coincidir por email,
    # username y document_number al mismo tiempo.
    unique_matches = {
        user.id: user
        for user in matches
    }

    matches = list(
        unique_matches.values()
    )

    if len(matches) > 1:

        ids = [
            user.id
            for user in matches
        ]

        raise RuntimeError(
            "Conflicto al sembrar empleado "
            f"{email}. "
            "El username/email/documento pertenecen "
            f"a usuarios diferentes: {ids}"
        )

    if not matches:
        return None

    return matches[0]


# =========================================================
# CREAR / ACTUALIZAR EMPLEADOS
# =========================================================

def seed_users(db):

    print("")
    print("======================================")
    print("           SEED EMPLEADOS")
    print("======================================")
    print("")

    print("Creando o actualizando empleados...")

    created_count = 0
    updated_count = 0

    for employee_data in EMPLOYEES:

        # -------------------------------------------------
        # BUSCAR ROL
        # -------------------------------------------------

        role = db.scalar(
            select(Role).where(
                Role.name
                == employee_data["role"]
            )
        )

        if not role:
            raise RuntimeError(
                f"No existe el rol "
                f"{employee_data['role']}"
            )

        # -------------------------------------------------
        # BUSCAR SI YA EXISTE
        # -------------------------------------------------

        existing_user = find_existing_seed_user(
            db=db,
            username=employee_data["username"],
            email=employee_data["email"],
            document_number=employee_data[
                "document_number"
            ],
        )

        # -------------------------------------------------
        # CREAR NUEVO
        # -------------------------------------------------

        if not existing_user:

            employee = User(
                username=
                    employee_data["username"],

                first_name=
                    employee_data["first_name"],

                last_name=
                    employee_data["last_name"],

                email=
                    employee_data["email"],

                password_hash=
                    hash_password(
                        employee_data["password"]
                    ),

                phone=
                    employee_data["phone"],

                document_number=
                    employee_data[
                        "document_number"
                    ],

                date_of_birth=
                    employee_data[
                        "date_of_birth"
                    ],

                role_id=
                    role.id,

                is_active=True,
                is_verified=True,
                profile_completed=True,
            )

            db.add(
                employee
            )

            # Ejecuta INSERT ahora para detectar
            # problemas dentro de esta iteración.
            db.flush()

            created_count += 1

            print(
                f"  + Creado: "
                f"{employee_data['email']}"
            )

            continue

        # -------------------------------------------------
        # ACTUALIZAR EXISTENTE
        # -------------------------------------------------

        old_email = existing_user.email
        old_username = existing_user.username

        existing_user.username = (
            employee_data["username"]
        )

        existing_user.first_name = (
            employee_data["first_name"]
        )

        existing_user.last_name = (
            employee_data["last_name"]
        )

        existing_user.email = (
            employee_data["email"]
        )

        existing_user.phone = (
            employee_data["phone"]
        )

        existing_user.document_number = (
            employee_data["document_number"]
        )

        existing_user.date_of_birth = (
            employee_data["date_of_birth"]
        )

        existing_user.role_id = role.id

        existing_user.is_active = True
        existing_user.is_verified = True
        existing_user.profile_completed = True

        # No regeneramos la contraseña cada vez
        # que ejecutamos el seed.
        #
        # Solo ponemos la contraseña del seed
        # cuando el usuario no tiene password.
        if not existing_user.password_hash:

            existing_user.password_hash = (
                hash_password(
                    employee_data["password"]
                )
            )

        db.flush()

        updated_count += 1

        if (
            old_email != employee_data["email"]
            or old_username
            != employee_data["username"]
        ):

            print(
                f"  ~ Actualizado: "
                f"{old_email} "
                f"-> {employee_data['email']}"
            )

        else:

            print(
                f"  - Ya existe: "
                f"{employee_data['email']}"
            )

    # -----------------------------------------------------
    # COMMIT FINAL
    # -----------------------------------------------------

    db.commit()

    print("")
    print(
        f"  + Empleados creados: "
        f"{created_count}"
    )

    print(
        f"  ~ Empleados actualizados/existentes: "
        f"{updated_count}"
    )

    print("")
    print(
        "  ✓ Seed de empleados completado"
    )
    print("")