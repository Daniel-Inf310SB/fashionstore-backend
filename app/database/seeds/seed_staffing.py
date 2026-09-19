from __future__ import annotations

from datetime import date

CITY_CODES = {
    "Santa Cruz de la Sierra": "sc",
    "La Paz": "lp",
    "Cochabamba": "cb",
    "Sucre": "su",
    "Oruro": "or",
    "Potosí": "pt",
    "Tarija": "tj",
    "Trinidad": "tr",
    "Cobija": "co",
}

MAJOR_CITIES = {
    "Santa Cruz de la Sierra",
    "La Paz",
    "Cochabamba",
}

FIRST_NAMES = [
    "Carlos", "María", "José", "Andrea", "Luis", "Fernanda",
    "Diego", "Gabriela", "Miguel", "Paola", "Marco", "Lucía",
    "Sergio", "Valeria", "Jorge", "Daniela", "Fernando", "Natalia",
]

LAST_NAMES = [
    "Rojas", "Flores", "Mendoza", "Quispe", "Vargas", "López",
    "Mamani", "Torrez", "Salazar", "Rivera", "Castro", "Morales",
    "Guzmán", "Vega", "Cabrera", "Ortiz", "Aguilar", "Suárez",
]

def build_staff_plan(branches: list[dict]) -> list[dict]:
    """
    Genera exactamente 1 encargado por sucursal y 1-2 cajeros.
    Las ciudades principales reciben 2 cajeros por sucursal; las demás, 1.
    """
    counters: dict[str, int] = {}
    plan: list[dict] = []
    employee_seq = 1

    for branch in branches:
        city = branch["city"]
        code = CITY_CODES[city]
        counters[city] = counters.get(city, 0) + 1
        branch_no = counters[city]

        roles = ["ENCARGADO_SUCURSAL"]
        roles.extend(["CAJERO"] * (2 if city in MAJOR_CITIES else 1))

        cashier_no = 0
        for role in roles:
            if role == "ENCARGADO_SUCURSAL":
                username = f"enc.{code}.{branch_no:02d}"
                email = f"encargado.{code}.{branch_no:02d}@fashionstore.com"
            else:
                cashier_no += 1
                username = f"caj.{code}.{branch_no:02d}.{cashier_no}"
                email = f"cajero.{code}.{branch_no:02d}.{cashier_no}@fashionstore.com"

            first = FIRST_NAMES[(employee_seq - 1) % len(FIRST_NAMES)]
            last = LAST_NAMES[(employee_seq * 3 - 1) % len(LAST_NAMES)]

            plan.append({
                "branch": branch["name"],
                "city": city,
                "username": username,
                "first_name": first,
                "last_name": last,
                "email": email,
                "password": "Empleado123*",
                "phone": f"72{employee_seq:06d}"[-8:],
                "document_number": f"FSE26{employee_seq:05d}",
                "date_of_birth": date(1987 + (employee_seq % 13), ((employee_seq - 1) % 12) + 1, ((employee_seq * 2) % 27) + 1),
                "role": role,
            })
            employee_seq += 1

    return plan
