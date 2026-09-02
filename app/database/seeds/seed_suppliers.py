from __future__ import annotations

from sqlalchemy.orm import Session

from app.models.supplier import Supplier

from app.database.seeds.seed_catalog_utils import (
    safe_bool_payload,
    upsert_model,
)


SUPPLIERS = [
    {
        "name": "Textiles Andinos",
        "business_name": "Textiles Andinos S.R.L.",
        "nit": "1020001001",
        "phone": "+591 70010001",
        "email": "ventas@textilesandinos.bo",
        "address": "Av. Blanco Galindo 1250, Cochabamba",
        "contact_name": "Carlos Mendoza",
    },
    {
        "name": "Moda Import Bolivia",
        "business_name": "Moda Import Bolivia Ltda.",
        "nit": "1020001002",
        "phone": "+591 70010002",
        "email": "comercial@modaimport.bo",
        "address": "Av. Brasil 845, La Paz",
        "contact_name": "María Quispe",
    },
    {
        "name": "Distribuidora Santa Cruz",
        "business_name": "Distribuidora Santa Cruz S.A.",
        "nit": "1020001003",
        "phone": "+591 70010003",
        "email": "ventas@distscz.bo",
        "address": "Av. Cristo Redentor 3200, Santa Cruz",
        "contact_name": "Jorge Ribera",
    },
    {
        "name": "Denim Bolivia",
        "business_name": "Denim Bolivia S.R.L.",
        "nit": "1020001004",
        "phone": "+591 70010004",
        "email": "pedidos@denimbolivia.bo",
        "address": "Av. América 1550, Cochabamba",
        "contact_name": "Daniela Vargas",
    },
    {
        "name": "Urban Wear Supply",
        "business_name": "Urban Wear Supply Ltda.",
        "nit": "1020001005",
        "phone": "+591 70010005",
        "email": "ventas@urbanwear.bo",
        "address": "Equipetrol Norte, Santa Cruz",
        "contact_name": "René Salvatierra",
    },
    {
        "name": "Confecciones Illimani",
        "business_name": "Confecciones Illimani S.R.L.",
        "nit": "1020001006",
        "phone": "+591 70010006",
        "email": "contacto@illimani.bo",
        "address": "Villa Fátima, La Paz",
        "contact_name": "Patricia Mamani",
    },
    {
        "name": "Fashion World Import",
        "business_name": "Fashion World Import S.R.L.",
        "nit": "1020001007",
        "phone": "+591 70010007",
        "email": "sales@fashionworld.bo",
        "address": "Av. Banzer 4200, Santa Cruz",
        "contact_name": "Luis Alberto Suárez",
    },
    {
        "name": "Prendas del Valle",
        "business_name": "Prendas del Valle S.R.L.",
        "nit": "1020001008",
        "phone": "+591 70010008",
        "email": "ventas@prendasdelvalle.bo",
        "address": "Av. Melchor Pérez 930, Cochabamba",
        "contact_name": "Ana Flores",
    },
    {
        "name": "Kids Moda Bolivia",
        "business_name": "Kids Moda Bolivia Ltda.",
        "nit": "1020001009",
        "phone": "+591 70010009",
        "email": "pedidos@kidsmoda.bo",
        "address": "Zona Central, La Paz",
        "contact_name": "Sofía Condori",
    },
    {
        "name": "Casual Style Import",
        "business_name": "Casual Style Import S.R.L.",
        "nit": "1020001010",
        "phone": "+591 70010010",
        "email": "ventas@casualstyle.bo",
        "address": "Av. Paraguá 2100, Santa Cruz",
        "contact_name": "Mauricio Rojas",
    },
    {
        "name": "Premium Garments",
        "business_name": "Premium Garments Bolivia S.R.L.",
        "nit": "1020001011",
        "phone": "+591 70010011",
        "email": "ventas@premiumgarments.bo",
        "address": "Calacoto, La Paz",
        "contact_name": "Andrea López",
    },
    {
        "name": "Bolivian Cotton",
        "business_name": "Bolivian Cotton S.R.L.",
        "nit": "1020001012",
        "phone": "+591 70010012",
        "email": "comercial@boliviancotton.bo",
        "address": "Parque Industrial, Santa Cruz",
        "contact_name": "Fernando Vaca",
    },
    {
        "name": "Street Line Supply",
        "business_name": "Street Line Supply Ltda.",
        "nit": "1020001013",
        "phone": "+591 70010013",
        "email": "ventas@streetline.bo",
        "address": "Av. Beijing 1210, Cochabamba",
        "contact_name": "Camila Arce",
    },
    {
        "name": "Importadora Aurora",
        "business_name": "Importadora Aurora S.R.L.",
        "nit": "1020001014",
        "phone": "+591 70010014",
        "email": "ventas@auroraimport.bo",
        "address": "Av. Arce 1880, La Paz",
        "contact_name": "Gabriel Nina",
    },
    {
        "name": "Global Fashion Supply",
        "business_name": "Global Fashion Supply Bolivia S.A.",
        "nit": "1020001015",
        "phone": "+591 70010015",
        "email": "sales@globalfashion.bo",
        "address": "Av. Doble Vía La Guardia, Santa Cruz",
        "contact_name": "Claudia Méndez",
    },
    {
        "name": "Ropa Urbana Bolivia",
        "business_name": "Ropa Urbana Bolivia S.R.L.",
        "nit": "1020001016",
        "phone": "+591 70010016",
        "email": "ventas@ropaurbana.bo",
        "address": "Zona Norte, Cochabamba",
        "contact_name": "Marco Torrico",
    },
    {
        "name": "Elegance Import",
        "business_name": "Elegance Import S.R.L.",
        "nit": "1020001017",
        "phone": "+591 70010017",
        "email": "ventas@elegance.bo",
        "address": "Av. San Martín, Santa Cruz",
        "contact_name": "Valeria Pinto",
    },
    {
        "name": "Confecciones Oriente",
        "business_name": "Confecciones Oriente Ltda.",
        "nit": "1020001018",
        "phone": "+591 70010018",
        "email": "pedidos@orienteconfecciones.bo",
        "address": "Plan 3000, Santa Cruz",
        "contact_name": "Raúl Chávez",
    },
    {
        "name": "Fashion Basics Bolivia",
        "business_name": "Fashion Basics Bolivia S.R.L.",
        "nit": "1020001019",
        "phone": "+591 70010019",
        "email": "ventas@fashionbasics.bo",
        "address": "Av. Heroínas 540, Cochabamba",
        "contact_name": "Natalia Rocha",
    },
    {
        "name": "Textil Premium",
        "business_name": "Textil Premium Bolivia S.R.L.",
        "nit": "1020001020",
        "phone": "+591 70010020",
        "email": "ventas@textilpremium.bo",
        "address": "Sopocachi, La Paz",
        "contact_name": "Ricardo Choque",
    },
]


def seed_suppliers(db: Session) -> None:

    print(
        "🌱 Seed proveedores: proveedores..."
    )

    for supplier_data in SUPPLIERS:

        upsert_model(
            db,
            Supplier,
            {
                **supplier_data,
                **safe_bool_payload(
                    Supplier,
                ),
            },
            lookup_field="nit",
        )

    db.flush()

    print(
        f"✅ Proveedores listos: {len(SUPPLIERS)}."
    )
