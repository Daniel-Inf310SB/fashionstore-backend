"""Plan de datos Multi-Tenant. Cantidades objetivo, no datos ya generados."""
from dataclasses import dataclass

@dataclass(frozen=True)
class TenantPlan:
    slug: str
    name: str
    branches: int
    managers_per_branch: int
    cashiers_per_branch: int
    customers: int
    products: int
    variants_per_product: int
    suppliers: int
    sales: int
    orders: int

FASHIONSTORE = TenantPlan('fashionstore', 'FashionStore', 27, 1, 2, 30, 120, 3, 20, 180, 90)
URBAN_STYLE = TenantPlan('urban-style-demo', 'Urban Style Demo', 2, 1, 2, 5, 12, 3, 3, 10, 5)
TECHNOVA = TenantPlan('technova-store', 'TechNova Store', 1, 1, 2, 5, 10, 3, 2, 10, 5)
DEMO_TENANTS = (FASHIONSTORE, URBAN_STYLE, TECHNOVA)
EXPECTED_DATABASE = 'fashionstore_db'
EXPECTED_ALEMBIC_HEAD = "a93b20261102"