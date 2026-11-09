"""Analítica descriptiva por tenant; K-Means exploratorio, no predicción real."""
from datetime import datetime, timedelta, timezone

import numpy as np
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.branch import Branch
from app.models.inventory import Inventory
from app.models.product import Product
from app.models.product_variant import ProductVariant
from app.models.sale import Sale
from app.models.sale_item import SaleItem


def tenant_analysis(db: Session, tenant_id: int, days: int = 90) -> dict:
    if not 7 <= days <= 365:
        raise ValueError('days debe estar entre 7 y 365')
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # Todos los filtros de pertenencia son explícitos; no confiar en ids enviados por clientes.
    products = db.query(Product.id, Product.name).filter(Product.tenant_id == tenant_id).order_by(Product.id).all()
    sales = (
        db.query(SaleItem.product_variant_id, func.sum(SaleItem.quantity), func.sum(SaleItem.subtotal))
        .join(Sale, SaleItem.sale_id == Sale.id)
        .join(Branch, Sale.branch_id == Branch.id)
        .join(ProductVariant, SaleItem.product_variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .filter(Sale.tenant_id == tenant_id, Branch.tenant_id == tenant_id,
                Product.tenant_id == tenant_id, Sale.status == 'PAID', Sale.created_at >= cutoff)
        .group_by(SaleItem.product_variant_id).all()
    )
    variants = db.query(ProductVariant.id, ProductVariant.product_id).join(Product, ProductVariant.product_id == Product.id).filter(Product.tenant_id == tenant_id).all()
    variant_to_product = {vid: pid for vid, pid in variants}
    by_product = {pid: {'units': 0, 'revenue': 0.0, 'available_stock': 0} for pid, _ in products}
    for vid, qty, revenue in sales:
        pid = variant_to_product.get(vid)
        if pid in by_product:
            by_product[pid]['units'] += int(qty or 0)
            by_product[pid]['revenue'] += float(revenue or 0)

    inventories = (
        db.query(ProductVariant.product_id,
                 func.sum(Inventory.stock_quantity - Inventory.reserved_quantity))
        .join(Branch, Inventory.branch_id == Branch.id)
        .join(ProductVariant, Inventory.product_variant_id == ProductVariant.id)
        .join(Product, ProductVariant.product_id == Product.id)
        .filter(Branch.tenant_id == tenant_id, Product.tenant_id == tenant_id)
        .group_by(ProductVariant.product_id).all()
    )
    for pid, available in inventories:
        if pid in by_product:
            by_product[pid]['available_stock'] = int(available or 0)

    rows = [{'product_id': pid, 'name': name, **by_product[pid]} for pid, name in products]
    result = {
        'data_source': 'REAL_TENANT_DATA', 'tenant_id': tenant_id, 'period_days': days,
        'analysis_type': 'DESCRIPTIVE_AND_EXPLORATORY',
        'prediction_available': False,
        'prediction_note': 'No se ha validado un predictor con historial real suficiente.',
        'summary': {'products': len(rows), 'units_sold': sum(x['units'] for x in rows),
                    'revenue_bob': round(sum(x['revenue'] for x in rows), 2),
                    'available_stock': sum(x['available_stock'] for x in rows)},
        'segmentation': {'available': False, 'reason': 'Se necesitan al menos 6 productos y variación suficiente.', 'clusters': []},
    }
    if len(rows) < 6:
        return result
    matrix = np.array([[x['units'], x['revenue'], x['available_stock']] for x in rows], dtype=float)
    if np.unique(matrix, axis=0).shape[0] < 3:
        return result
    scaled = StandardScaler().fit_transform(matrix)
    fitted = KMeans(n_clusters=3, random_state=2026, n_init=10).fit(scaled)
    groups = []
    for label in sorted(set(fitted.labels_)):
        selected = [rows[i] for i, c in enumerate(fitted.labels_) if c == label]
        groups.append({'cluster_id': int(label), 'products': len(selected),
                       'average_units_sold': round(sum(v['units'] for v in selected) / len(selected), 2),
                       'average_available_stock': round(sum(v['available_stock'] for v in selected) / len(selected), 2),
                       'average_revenue_bob': round(sum(v['revenue'] for v in selected) / len(selected), 2)})
    result['segmentation'] = {'available': True,
                               'note': 'Grupos exploratorios calculados con información real del tenant. Las etiquetas no son categorías fijas.',
                               'clusters': groups}
    return result
