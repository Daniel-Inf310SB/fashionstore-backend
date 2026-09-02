from __future__ import annotations

from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.product import Product

from app.database.seeds.seed_catalog_utils import (
    add_relation_if_missing,
    first_existing_field,
    safe_bool_payload,
)


def _product_base_price(product) -> Decimal:

    value = (
        getattr(
            product,
            "base_price",
            None,
        )
        or getattr(
            product,
            "price",
            None,
        )
        or Decimal("100.00")
    )

    return Decimal(
        str(value)
    )


def seed_supplier_products(
    db: Session,
) -> None:

    print(
        "🌱 Seed proveedores: productos por proveedor..."
    )

    suppliers = list(
        db.scalars(
            select(Supplier)
            .where(
                Supplier.is_active.is_(True)
            )
            .order_by(
                Supplier.id
            )
        ).all()
    )

    products = list(
        db.scalars(
            select(Product)
            .order_by(
                Product.id
            )
        ).all()
    )

    if not suppliers:

        raise RuntimeError(
            "No hay proveedores. Ejecuta seed_suppliers primero."
        )

    if not products:

        raise RuntimeError(
            "No hay productos. Ejecuta primero el seed del catálogo."
        )

    processed = 0

    for product_index, product in enumerate(
        products,
        start=1,
    ):

        # Cada producto queda asociado con 2 proveedores.
        supplier_indexes = {
            product_index % len(suppliers),
            (product_index * 3 + 5) % len(suppliers),
        }

        for position, supplier_index in enumerate(
            sorted(supplier_indexes),
            start=1,
        ):

            supplier = suppliers[
                supplier_index
            ]

            retail_price = _product_base_price(
                product
            )

            # Compra aproximada entre 52% y 66% del precio de venta.
            factor = Decimal(
                str(
                    0.52
                    + (
                        (
                            product_index
                            + supplier.id
                            + position
                        )
                        % 8
                    )
                    * 0.02
                )
            )

            purchase_price = (
                retail_price
                * factor
            ).quantize(
                Decimal("0.01")
            )

            supplier_code = (
                f"SUP-{supplier.id:03d}-"
                f"PRD-{product.id:05d}"
            )

            payload = {
                "supplier_id":
                    supplier.id,

                "product_id":
                    product.id,

                "supplier_code":
                    supplier_code,

                "purchase_price":
                    purchase_price,

                "minimum_order_quantity":
                    5
                    + (
                        (
                            product_index
                            + supplier.id
                        )
                        % 5
                    )
                    * 5,

                "lead_time_days":
                    1
                    + (
                        (
                            product_index
                            + supplier.id
                        )
                        % 7
                    ),

                **safe_bool_payload(
                    SupplierProduct,
                ),
            }

            # La relación natural ya tiene UNIQUE:
            # supplier_id + product_id
            add_relation_if_missing(
                db,
                SupplierProduct,
                payload,
                unique_by=(
                    "supplier_id",
                    "product_id",
                ),
            )

            processed += 1

    db.flush()

    print(
        f"✅ Productos de proveedor procesados: {processed}."
    )
