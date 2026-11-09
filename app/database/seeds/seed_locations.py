"""Crea ciudades globales y sucursales con tenant. Sin commits."""
from sqlalchemy import select
from app.models.city import City
from app.models.branch import Branch
from app.database.seeds.seed_reference_data import CITIES, BRANCHES

def seed_locations(db, tenant_ids):
    cities = {}
    for name in CITIES:
        city = db.scalar(select(City).where(City.name == name))
        if city is None:
            city = City(name=name, is_active=True)
            db.add(city)
            db.flush()
        cities[name] = city
    plans = [(tenant_ids["fashionstore"], item) for item in BRANCHES]
    plans += [
        (tenant_ids["urban-style-demo"], {"name": "Urban Style Centro", "city": "Santa Cruz de la Sierra", "address": "Zona Centro, Santa Cruz de la Sierra"}),
        (tenant_ids["urban-style-demo"], {"name": "Urban Style Norte", "city": "Santa Cruz de la Sierra", "address": "Zona Norte, Santa Cruz de la Sierra"}),
    ]
    plans += [(tenant_ids["technova-store"], {"name": "TechNova Centro", "city": "Santa Cruz de la Sierra", "address": "Zona Centro, Santa Cruz de la Sierra"})]
    result = []
    for tenant_id, spec in plans:
        branch = db.scalar(select(Branch).where(Branch.tenant_id == tenant_id, Branch.name == spec["name"]))
        if branch is None:
            branch = Branch(tenant_id=tenant_id, name=spec["name"], address=spec["address"], city_id=cities[spec["city"]].id,
                            phone=spec.get("phone"), latitude=spec.get("latitude"), longitude=spec.get("longitude"), is_active=True)
            db.add(branch)
            db.flush()
        elif branch.city_id != cities[spec["city"]].id:
            raise RuntimeError(f"Sucursal {branch.name} tiene una ciudad distinta a la esperada")
        result.append(branch)
    if len(result) != 30:
        raise RuntimeError(f"Se esperaban 30 sucursales, hay {len(result)}")
    return result
