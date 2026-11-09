"""Bloque 4: stock por sucursal y entradas trazables de proveedores.

Idempotente: no reescribe inventarios existentes ni repite movimientos.
Una fila nueva Inventory se acompana de un movimiento ENTRY.
"""
from decimal import Decimal
from sqlalchemy import select, func
from app.database.seeds.seed_demo_config import DEMO_TENANTS
from app.models.branch import Branch
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.inventory import Inventory
from app.models.inventory_movement import InventoryMovement
from app.models.supplier import Supplier
from app.models.supplier_product import SupplierProduct
from app.models.supplier_availability import SupplierAvailability


def seed_inventory_multitenant(db, tenant_ids):
    summary = {}
    for spec in DEMO_TENANTS:
        tid = tenant_ids[spec.slug]
        branches = db.scalars(select(Branch).where(Branch.tenant_id == tid).order_by(Branch.id)).all()
        products = db.scalars(select(Product).where(Product.tenant_id == tid).order_by(Product.id)).all()
        if len(branches) != spec.branches or len(products) != spec.products:
            raise RuntimeError(f"Bloque 2/3 incompleto en {spec.slug}: {len(branches)} sucursales, {len(products)} productos")

        # Carga previa y lectura estrictamente filtrada por empresa.
        supplier_links = db.execute(
            select(SupplierProduct, Supplier).join(Supplier, Supplier.id == SupplierProduct.supplier_id)
            .join(Product, Product.id == SupplierProduct.product_id)
            .where(Product.tenant_id == tid, Supplier.tenant_id == tid, SupplierProduct.is_active.is_(True))
            .order_by(SupplierProduct.id)
        ).all()
        by_product = {}
        for link, supplier in supplier_links:
            by_product.setdefault(link.product_id, (link, supplier))

        variants = db.execute(
            select(ProductVariant.id, ProductVariant.product_id)
            .join(Product, Product.id == ProductVariant.product_id)
            .where(Product.tenant_id == tid).order_by(Product.id, ProductVariant.id)
        ).all()
        if len(variants) != spec.products * spec.variants_per_product:
            raise RuntimeError(f"Variantes incompletas para {spec.slug}: {len(variants)}")
        if any(pid not in by_product for _, pid in variants):
            raise RuntimeError(f"Hay productos sin proveedor en {spec.slug}")

        # Prevenir mezcla con otros tenants y no insertar datos por accidente.
        existing = db.execute(
            select(Inventory.id, Inventory.branch_id, Inventory.product_variant_id)
            .join(Branch, Branch.id == Inventory.branch_id)
            .where(Branch.tenant_id == tid)
        ).all()
        existing_pairs = {(b, v) for _, b, v in existing}
        valid_branches = {b.id for b in branches}
        valid_variants = {v for v, _ in variants}
        unexpected = [(b, v) for _, b, v in existing if b not in valid_branches or v not in valid_variants]
        if unexpected:
            raise RuntimeError(f"Inventarios cruzados o fuera del catalogo en {spec.slug}: {unexpected[:3]}")

        created = 0
        skipped = 0
        entry_qty = 0
        low = 0
        zero = 0
        for bi, branch in enumerate(branches):
            for vi, (variant_id, product_id) in enumerate(variants):
                pair = (branch.id, variant_id)
                if pair in existing_pairs:
                    skipped += 1
                    continue
                # Precios y proveedor reales de la relacion creada en Bloque 3.
                link, supplier = by_product[product_id]
                if branch.tenant_id != supplier.tenant_id:
                    raise RuntimeError("Cruce de empresas en entrada de stock")
                # Distribucion reproducible: normal, bajo y agotado.
                key = (bi * 7 + vi * 3) % 31
                if key == 0:
                    qty = 0
                    zero += 1
                elif key in (1, 2, 3):
                    qty = 2 + (vi % 3)
                    low += 1
                else:
                    qty = 18 + ((bi + vi) % 29)
                inv = Inventory(branch_id=branch.id, product_variant_id=variant_id,
                                stock_quantity=qty, reserved_quantity=0,
                                minimum_stock=5, maximum_stock=100, reorder_point=7, is_active=True)
                db.add(inv)
                db.flush()
                # No generar movimientos de cantidad cero: check quantity > 0.
                if qty > 0:
                    ref = f"SEED-B4-T{tid}-B{branch.id}-V{variant_id}"
                    movement = InventoryMovement(
                        inventory_id=inv.id, movement_type="ENTRY", quantity=qty,
                        stock_before=0, stock_after=qty,
                        reserved_before=0, reserved_after=0,
                        supplier_id=supplier.id, user_id=None,
                        unit_cost=Decimal(link.purchase_price),
                        reference_type="SEED_INITIAL_STOCK", reference_code=ref,
                        reason="Abastecimiento inicial de demostracion",
                        notes=f"Proveedor {supplier.name}; SupplierProduct #{link.id}. Datos de prueba."
                    )
                    db.add(movement)
                    entry_qty += qty
                created += 1
        db.flush()
        summary[spec.slug] = dict(branches=len(branches), variants=len(variants),
                                  inventories_created=created, inventories_existing=skipped,
                                  units_entered=entry_qty, stock_low_created=low, stock_zero_created=zero)
    return summary
