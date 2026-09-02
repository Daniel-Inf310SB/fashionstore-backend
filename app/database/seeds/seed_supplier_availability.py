from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier_product import SupplierProduct
from app.models.supplier_availability import SupplierAvailability
from app.models.product_variant import ProductVariant

from app.database.seeds.seed_catalog_utils import (
    add_relation_if_missing,
)


def _status_for_quantity(
    quantity: int,
) -> str:

    if quantity <= 0:
        return "OUT_OF_STOCK"

    if quantity <= 20:
        return "LOW_STOCK"

    return "AVAILABLE"


def seed_supplier_availability(
    db: Session,
) -> None:

    print(
        "🌱 Seed proveedores: disponibilidad por variante..."
    )

    supplier_products = list(
        db.scalars(
            select(SupplierProduct)
            .where(
                SupplierProduct.is_active.is_(True)
            )
            .order_by(
                SupplierProduct.id
            )
        ).all()
    )

    if not supplier_products:

        raise RuntimeError(
            "No hay SupplierProduct. "
            "Ejecuta seed_supplier_products primero."
        )

    processed = 0

    for supplier_product in supplier_products:

        variants = list(
            db.scalars(
                select(ProductVariant)
                .where(
                    ProductVariant.product_id
                    == supplier_product.product_id
                )
                .order_by(
                    ProductVariant.id
                )
            ).all()
        )

        if not variants:
            continue

        for variant_index, variant in enumerate(
            variants,
            start=1,
        ):

            # Valores determinísticos.
            raw_quantity = (
                (
                    supplier_product.id
                    * 17
                )
                + (
                    variant.id
                    * 11
                )
                + variant_index
            ) % 151

            # Algunos casos se fuerzan a agotado.
            if (
                supplier_product.id
                + variant_index
            ) % 19 == 0:
                quantity = 0
            else:
                quantity = raw_quantity

            status = _status_for_quantity(
                quantity
            )

            base_purchase_price = Decimal(
                str(
                    supplier_product.purchase_price
                )
            )

            # Pequeña diferencia de costo por variante.
            variant_adjustment = Decimal(
                str(
                    (
                        variant_index
                        % 4
                    )
                    * 1.50
                )
            )

            purchase_price = (
                base_purchase_price
                + variant_adjustment
            ).quantize(
                Decimal("0.01")
            )

            add_relation_if_missing(
                db,
                SupplierAvailability,
                {
                    "supplier_product_id":
                        supplier_product.id,

                    "product_variant_id":
                        variant.id,

                    "available_quantity":
                        quantity,

                    "status":
                        status,

                    "purchase_price":
                        purchase_price,
                },
                unique_by=(
                    "supplier_product_id",
                    "product_variant_id",
                ),
            )

            processed += 1

    db.flush()

    print(
        f"✅ Disponibilidades procesadas: {processed}."
    )
