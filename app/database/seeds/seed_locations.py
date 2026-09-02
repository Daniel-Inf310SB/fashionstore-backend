from sqlalchemy import select

from app.models.city import City
from app.models.branch import Branch
from app.models.employee_branch import EmployeeBranch
from app.models.user import User


# =========================================================
# CIUDADES
# =========================================================

CITIES = [
    "Santa Cruz de la Sierra",
    "La Paz",
    "Cochabamba",
    "Sucre",
    "Oruro",
    "Potosí",
    "Tarija",
    "Trinidad",
    "Cobija",
]


# =========================================================
# SUCURSALES
# =========================================================

BRANCHES = [
    # Santa Cruz de la Sierra
    {
        "name": "FashionStore Equipetrol",
        "address": "Av. San Martín, zona Equipetrol, Santa Cruz de la Sierra",
        "phone": "33600001",
        "city": "Santa Cruz de la Sierra",
        "latitude": -17.7696,
        "longitude": -63.1952,
    },
    {
        "name": "FashionStore Centro SC",
        "address": "Calle 24 de Septiembre, Centro, Santa Cruz de la Sierra",
        "phone": "33600002",
        "city": "Santa Cruz de la Sierra",
        "latitude": -17.7833,
        "longitude": -63.1821,
    },
    {
        "name": "FashionStore Ventura",
        "address": "Av. San Martín, Equipetrol Norte, Santa Cruz de la Sierra",
        "phone": "33600003",
        "city": "Santa Cruz de la Sierra",
        "latitude": -17.765,
        "longitude": -63.1965,
    },

    # La Paz
    {
        "name": "FashionStore Sopocachi",
        "address": "Av. 20 de Octubre, Sopocachi, La Paz",
        "phone": "22400001",
        "city": "La Paz",
        "latitude": -16.5105,
        "longitude": -68.1278,
    },
    {
        "name": "FashionStore Calacoto",
        "address": "Av. Ballivián, Calacoto, La Paz",
        "phone": "22400002",
        "city": "La Paz",
        "latitude": -16.5406,
        "longitude": -68.0868,
    },
    {
        "name": "FashionStore Centro LP",
        "address": "Av. Mariscal Santa Cruz, Centro, La Paz",
        "phone": "22400003",
        "city": "La Paz",
        "latitude": -16.4957,
        "longitude": -68.1335,
    },

    # Cochabamba
    {
        "name": "FashionStore Cala Cala",
        "address": "Av. América Oeste, Cala Cala, Cochabamba",
        "phone": "44200001",
        "city": "Cochabamba",
        "latitude": -17.3741,
        "longitude": -66.1633,
    },
    {
        "name": "FashionStore Queru Queru",
        "address": "Av. Melchor Urquidi, Queru Queru, Cochabamba",
        "phone": "44200002",
        "city": "Cochabamba",
        "latitude": -17.3732,
        "longitude": -66.1578,
    },
    {
        "name": "FashionStore Centro CBBA",
        "address": "Av. Heroínas, Centro, Cochabamba",
        "phone": "44200003",
        "city": "Cochabamba",
        "latitude": -17.3935,
        "longitude": -66.157,
    },

    # Sucre
    {
        "name": "FashionStore Sucre Centro",
        "address": "Calle Aniceto Arce, Centro Histórico, Sucre",
        "phone": "46400001",
        "city": "Sucre",
        "latitude": -19.0476,
        "longitude": -65.2596,
    },
    {
        "name": "FashionStore Sucre Norte",
        "address": "Av. de las Américas, zona Norte, Sucre",
        "phone": "46400002",
        "city": "Sucre",
        "latitude": -19.0328,
        "longitude": -65.2524,
    },
    {
        "name": "FashionStore Sucre Sur",
        "address": "Av. Marcelo Quiroga Santa Cruz, zona Sur, Sucre",
        "phone": "46400003",
        "city": "Sucre",
        "latitude": -19.061,
        "longitude": -65.256,
    },

    # Oruro
    {
        "name": "FashionStore Oruro Centro",
        "address": "Calle Bolívar, Centro, Oruro",
        "phone": "25200001",
        "city": "Oruro",
        "latitude": -17.97,
        "longitude": -67.1147,
    },
    {
        "name": "FashionStore Oruro Norte",
        "address": "Av. 6 de Agosto, zona Norte, Oruro",
        "phone": "25200002",
        "city": "Oruro",
        "latitude": -17.9535,
        "longitude": -67.1128,
    },
    {
        "name": "FashionStore Oruro Sur",
        "address": "Av. España, zona Sur, Oruro",
        "phone": "25200003",
        "city": "Oruro",
        "latitude": -17.989,
        "longitude": -67.112,
    },

    # Potosí
    {
        "name": "FashionStore Potosí Centro",
        "address": "Calle Bolívar, Centro, Potosí",
        "phone": "26200001",
        "city": "Potosí",
        "latitude": -19.5885,
        "longitude": -65.7535,
    },
    {
        "name": "FashionStore Potosí Norte",
        "address": "Av. Universitaria, zona Norte, Potosí",
        "phone": "26200002",
        "city": "Potosí",
        "latitude": -19.574,
        "longitude": -65.756,
    },
    {
        "name": "FashionStore Potosí Sur",
        "address": "Av. Las Banderas, zona Sur, Potosí",
        "phone": "26200003",
        "city": "Potosí",
        "latitude": -19.606,
        "longitude": -65.7565,
    },

    # Tarija
    {
        "name": "FashionStore Tarija Centro",
        "address": "Calle General Trigo, Centro, Tarija",
        "phone": "46600001",
        "city": "Tarija",
        "latitude": -21.5355,
        "longitude": -64.7296,
    },
    {
        "name": "FashionStore Tarija Norte",
        "address": "Av. Víctor Paz Estenssoro, zona Norte, Tarija",
        "phone": "46600002",
        "city": "Tarija",
        "latitude": -21.52,
        "longitude": -64.7315,
    },
    {
        "name": "FashionStore Tarija Sur",
        "address": "Av. La Paz, zona Sur, Tarija",
        "phone": "46600003",
        "city": "Tarija",
        "latitude": -21.548,
        "longitude": -64.7255,
    },

    # Trinidad
    {
        "name": "FashionStore Trinidad Centro",
        "address": "Av. 6 de Agosto, Centro, Trinidad",
        "phone": "34600001",
        "city": "Trinidad",
        "latitude": -14.8347,
        "longitude": -64.9044,
    },
    {
        "name": "FashionStore Trinidad Norte",
        "address": "Av. Panamericana, zona Norte, Trinidad",
        "phone": "34600002",
        "city": "Trinidad",
        "latitude": -14.8205,
        "longitude": -64.9005,
    },
    {
        "name": "FashionStore Trinidad Sur",
        "address": "Av. 18 de Noviembre, zona Sur, Trinidad",
        "phone": "34600003",
        "city": "Trinidad",
        "latitude": -14.8495,
        "longitude": -64.904,
    },

    # Cobija
    {
        "name": "FashionStore Cobija Centro",
        "address": "Av. 9 de Febrero, Centro, Cobija",
        "phone": "38400001",
        "city": "Cobija",
        "latitude": -11.0267,
        "longitude": -68.7692,
    },
    {
        "name": "FashionStore Cobija Norte",
        "address": "Av. Internacional, zona Norte, Cobija",
        "phone": "38400002",
        "city": "Cobija",
        "latitude": -11.0145,
        "longitude": -68.7655,
    },
    {
        "name": "FashionStore Cobija Sur",
        "address": "Av. Pando, zona Sur, Cobija",
        "phone": "38400003",
        "city": "Cobija",
        "latitude": -11.04,
        "longitude": -68.772,
    },
]


# =========================================================
# ASIGNACIONES
# =========================================================

EMPLOYEE_ASSIGNMENTS = [

    # Santa Cruz
    {
        "email": "encargado.sc@fashionstore.com",
        "branch": "FashionStore Equipetrol",
    },
    {
        "email": "cajero.sc1@fashionstore.com",
        "branch": "FashionStore Centro SC",
    },
    {
        "email": "cajero.sc2@fashionstore.com",
        "branch": "FashionStore Ventura",
    },


    # La Paz
    {
        "email": "encargado.lp@fashionstore.com",
        "branch": "FashionStore Sopocachi",
    },
    {
        "email": "cajero.lp1@fashionstore.com",
        "branch": "FashionStore Calacoto",
    },
    {
        "email": "cajero.lp2@fashionstore.com",
        "branch": "FashionStore Centro LP",
    },


    # Cochabamba
    {
        "email": "encargado.cbba@fashionstore.com",
        "branch": "FashionStore Cala Cala",
    },
    {
        "email": "cajero.cbba1@fashionstore.com",
        "branch": "FashionStore Queru Queru",
    },
    {
        "email": "cajero.cbba2@fashionstore.com",
        "branch": "FashionStore Centro CBBA",
    },


    # Chuquisaca
    {
        "email": "encargado.ch@fashionstore.com",
        "branch": "FashionStore Sucre Centro",
    },
    {
        "email": "cajero.ch1@fashionstore.com",
        "branch": "FashionStore Sucre Norte",
    },
    {
        "email": "cajero.ch2@fashionstore.com",
        "branch": "FashionStore Sucre Sur",
    },


    # Oruro
    {
        "email": "encargado.or@fashionstore.com",
        "branch": "FashionStore Oruro Centro",
    },
    {
        "email": "cajero.or1@fashionstore.com",
        "branch": "FashionStore Oruro Norte",
    },
    {
        "email": "cajero.or2@fashionstore.com",
        "branch": "FashionStore Oruro Sur",
    },


    # Potosí
    {
        "email": "encargado.pt@fashionstore.com",
        "branch": "FashionStore Potosí Centro",
    },
    {
        "email": "cajero.pt1@fashionstore.com",
        "branch": "FashionStore Potosí Norte",
    },
    {
        "email": "cajero.pt2@fashionstore.com",
        "branch": "FashionStore Potosí Sur",
    },


    # Tarija
    {
        "email": "encargado.tj@fashionstore.com",
        "branch": "FashionStore Tarija Centro",
    },
    {
        "email": "cajero.tj1@fashionstore.com",
        "branch": "FashionStore Tarija Norte",
    },
    {
        "email": "cajero.tj2@fashionstore.com",
        "branch": "FashionStore Tarija Sur",
    },


    # Beni
    {
        "email": "encargado.be@fashionstore.com",
        "branch": "FashionStore Trinidad Centro",
    },
    {
        "email": "cajero.be1@fashionstore.com",
        "branch": "FashionStore Trinidad Norte",
    },
    {
        "email": "cajero.be2@fashionstore.com",
        "branch": "FashionStore Trinidad Sur",
    },


    # Pando
    {
        "email": "encargado.pd@fashionstore.com",
        "branch": "FashionStore Cobija Centro",
    },
    {
        "email": "cajero.pd1@fashionstore.com",
        "branch": "FashionStore Cobija Norte",
    },
    {
        "email": "cajero.pd2@fashionstore.com",
        "branch": "FashionStore Cobija Sur",
    },
]


# =========================================================
# CREAR CIUDADES
# =========================================================

def seed_cities(db):

    print("Creando ciudades...")

    for city_name in CITIES:

        city = db.scalar(
            select(City).where(
                City.name == city_name
            )
        )

        if city:
            print(
                f"  - Ciudad {city_name} ya existe"
            )
            continue

        city = City(
            name=city_name,
            is_active=True,
        )

        db.add(city)

        print(
            f"  + Ciudad creada: {city_name}"
        )

    db.commit()


# =========================================================
# CREAR SUCURSALES
# =========================================================

def seed_branches(db):

    print("Creando o actualizando sucursales...")

    for branch_data in BRANCHES:

        city = db.scalar(
            select(City).where(
                City.name == branch_data["city"]
            )
        )

        if not city:
            raise RuntimeError(
                f"No existe la ciudad "
                f"{branch_data['city']}"
            )

        branch = db.scalar(
            select(Branch).where(
                Branch.name == branch_data["name"]
            )
        )

        # =================================================
        # CREAR SUCURSAL SI NO EXISTE
        # =================================================

        if not branch:

            branch = Branch(
                name=branch_data["name"],
                address=branch_data["address"],
                phone=branch_data["phone"],
                latitude=branch_data["latitude"],
                longitude=branch_data["longitude"],
                city_id=city.id,
                is_active=True,
            )

            db.add(branch)

            print(
                f"  + Sucursal creada: "
                f"{branch_data['name']}"
            )

            continue

        # =================================================
        # ACTUALIZAR SOLO CAMPOS VACÍOS
        # =================================================

        updated_fields = []

        if not branch.address:
            branch.address = branch_data["address"]
            updated_fields.append("address")

        if not branch.phone:
            branch.phone = branch_data["phone"]
            updated_fields.append("phone")

        if branch.latitude is None:
            branch.latitude = branch_data["latitude"]
            updated_fields.append("latitude")

        if branch.longitude is None:
            branch.longitude = branch_data["longitude"]
            updated_fields.append("longitude")

        if branch.city_id is None:
            branch.city_id = city.id
            updated_fields.append("city_id")

        if updated_fields:
            print(
                f"  ~ {branch.name} actualizado: "
                f"{', '.join(updated_fields)}"
            )
        else:
            print(
                f"  - {branch.name} ya está completo"
            )

    db.commit()



# =========================================================
# ASIGNAR EMPLEADOS
# =========================================================

def seed_employee_branches(db):

    print(
        "Asignando empleados a sucursales..."
    )

    for assignment_data in EMPLOYEE_ASSIGNMENTS:

        user = db.scalar(
            select(User).where(
                User.email
                == assignment_data["email"]
            )
        )

        if not user:
            print(
                f"  ! Usuario no encontrado: "
                f"{assignment_data['email']}"
            )
            continue

        branch = db.scalar(
            select(Branch).where(
                Branch.name
                == assignment_data["branch"]
            )
        )

        if not branch:
            print(
                f"  ! Sucursal no encontrada: "
                f"{assignment_data['branch']}"
            )
            continue

        existing_assignment = db.scalar(
            select(EmployeeBranch).where(
                EmployeeBranch.user_id
                == user.id,

                EmployeeBranch.branch_id
                == branch.id,

                EmployeeBranch.is_active
                == True,
            )
        )

        if existing_assignment:
            print(
                f"  - {user.email} ya está "
                f"asignado a {branch.name}"
            )
            continue

        # -------------------------------------------------
        # Evitar que el mismo empleado tenga otra sucursal
        # activa al mismo tiempo
        # -------------------------------------------------

        another_active_assignment = db.scalar(
            select(EmployeeBranch).where(
                EmployeeBranch.user_id
                == user.id,

                EmployeeBranch.is_active
                == True,
            )
        )

        if another_active_assignment:

            another_active_assignment.is_active = False

            another_active_assignment.ended_at = (
                another_active_assignment.assigned_at
            )

        assignment = EmployeeBranch(
            user_id=user.id,
            branch_id=branch.id,
            is_active=True,
        )

        db.add(assignment)

        print(
            f"  + {user.email} "
            f"-> {branch.name}"
        )

    db.commit()


# =========================================================
# EJECUTAR
# =========================================================

def seed_locations(db):

    print("")
    print(
        "======================================"
    )
    print(
        "         SEED LOCATIONS"
    )
    print(
        "======================================"
    )
    print("")

    seed_cities(db)

    seed_branches(db)

    seed_employee_branches(db)

    print("")
    print(
        "  ✓ Ciudades, sucursales "
        "y asignaciones completadas"
    )
    print("")