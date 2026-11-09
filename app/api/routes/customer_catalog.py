from app.api.routes.store_branches import resolve_storefront_tenant
from decimal import Decimal

from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    Query,
)

from sqlalchemy.orm import (
    Session,
)

from app.database.session import (
    get_db,
)

from app.schemas.customer_catalog import (
    CustomerCatalogListResponse,
)

from app.services.customer_catalog import (
    CustomerCatalogService,
)


router = APIRouter(
    prefix="/store/catalog",

    tags=[
        "Store - Customer Catalog"
    ],
)


# Opciones de filtros basadas exclusivamente en los productos de esta empresa y sucursal.
@router.get("/facets")
def get_catalog_facets(
    branch_id: int = Query(..., ge=1),
    tenant_slug: str | None = Query(default=None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    from app.models.branch import Branch
    from app.models.product import Product
    from app.models.category import Category
    from app.models.audience import Audience
    from app.models.product_variant import ProductVariant
    from app.models.inventory import Inventory
    from app.models.size import Size
    from app.models.color import Color

    tenant = resolve_storefront_tenant(db, tenant_slug)
    branch = db.query(Branch.id).filter(
        Branch.id == branch_id,
        Branch.tenant_id == tenant.id,
        Branch.is_active.is_(True),
    ).first()
    if branch is None:
        raise HTTPException(status_code=404, detail="Sucursal no disponible en esta empresa.")

    products = db.query(Product.id).filter(
        Product.tenant_id == tenant.id, Product.is_active.is_(True)
    ).subquery()
    variants = db.query(ProductVariant.id, ProductVariant.product_id,
                        ProductVariant.size_id, ProductVariant.color_id).join(
        products, ProductVariant.product_id == products.c.id
    ).join(Inventory, Inventory.product_variant_id == ProductVariant.id).filter(
        Inventory.branch_id == branch_id, ProductVariant.is_active.is_(True)
    ).subquery()

    categories = db.query(Category.id, Category.name).join(
        Product, Product.category_id == Category.id
    ).join(variants, variants.c.product_id == Product.id).filter(
        Product.tenant_id == tenant.id, Product.is_active.is_(True)
    ).distinct().order_by(Category.name).all()
    audiences = db.query(Audience.id, Audience.name).join(
        Product, Product.audience_id == Audience.id
    ).join(variants, variants.c.product_id == Product.id).filter(
        Product.tenant_id == tenant.id, Product.is_active.is_(True)
    ).distinct().order_by(Audience.name).all()
    sizes = db.query(Size.id, Size.name).join(
        variants, variants.c.size_id == Size.id
    ).distinct().order_by(Size.name).all()
    colors = db.query(Color.id, Color.name).join(
        variants, variants.c.color_id == Color.id
    ).distinct().order_by(Color.name).all()
    return {
        "audiences": [{"id": id, "name": name} for id, name in audiences],
        "categories": [{"id": id, "name": name} for id, name in categories],
        "sizes": [{"id": id, "name": name} for id, name in sizes],
        "colors": [{"id": id, "name": name} for id, name in colors],
    }


# =========================================================
# CU24 - CONSULTAR CATÁLOGO
# CU25 - BUSCAR Y FILTRAR PRENDAS
# =========================================================

@router.get(
    "",
    response_model=
        CustomerCatalogListResponse,
)
def get_customer_catalog(

    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=12,
        ge=1,
        le=100,
    ),

    # =====================================================
    # SUCURSAL OPCIONAL
    # =====================================================

    branch_id: int | None = Query(
        default=None,
        ge=1,
    ),

    search: str | None = Query(
        default=None,
        min_length=1,
        max_length=150,
    ),

    audience: str | None = Query(
        default=None,
        min_length=1,
        max_length=50,
    ),

    category: str | None = Query(
        default=None,
        min_length=1,
        max_length=100,
    ),

    size_id: int | None = Query(
        default=None,
        ge=1,
    ),

    color_id: int | None = Query(
        default=None,
        ge=1,
    ),

    min_price: Decimal | None = Query(
        default=None,
        ge=0,
    ),

    max_price: Decimal | None = Query(
        default=None,
        ge=0,
    ),

    promotion: bool | None = Query(
        default=None,
    ),

    promotion_id: int | None = Query(
        default=None,
        ge=1,
    ),

    collection_id: int | None = Query(
        default=None,
        ge=1,
    ),

    season_id: int | None = Query(
        default=None,
        ge=1,
    ),

    in_stock: bool | None = Query(
        default=None,
    ),

    sort_by: Literal[
        "name",
        "price",
        "created_at",
    ] = Query(
        default="name",
    ),

    sort_order: Literal[
        "asc",
        "desc",
    ] = Query(
        default="asc",
    ),

    db: Session = Depends(
        get_db
    ),
    tenant_slug: str | None = Query(default=None, min_length=1, max_length=100),
):

    return (
        CustomerCatalogService
        .get_catalog(
            db=db,

            tenant_id=resolve_storefront_tenant(db, tenant_slug).id,

            page=page,

            page_size=
                page_size,

            branch_id=
                branch_id,

            search=
                search,

            audience=
                audience,

            category=
                category,

            size_id=
                size_id,

            color_id=
                color_id,

            min_price=
                min_price,

            max_price=
                max_price,

            promotion=
                promotion,

            promotion_id=
                promotion_id,

            collection_id=
                collection_id,

            season_id=
                season_id,

            in_stock=
                in_stock,

            sort_by=
                sort_by,

            sort_order=
                sort_order,
        )
    )