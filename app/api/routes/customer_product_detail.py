from uuid import UUID
from app.api.routes.store_branches import resolve_storefront_tenant
from fastapi import (
    APIRouter,
    Depends,
    Path,
    Query,
)

from sqlalchemy.orm import (
    Session,
)

from app.database.session import (
    get_db,
)

from app.schemas.customer_product_detail import (
    CustomerProductAvailabilityResponse,
    CustomerProductDetailResponse,
)

from app.services.customer_product_detail import (
    CustomerProductDetailService,
)


router = APIRouter(
    prefix="/store/products",

    tags=[
        "Store - Customer Products"
    ],
)


# Identificador público; los IDs internos continúan usándose en carrito y pedidos.
@router.get("/public/{public_id}")
def resolve_public_product(
    public_id: UUID,
    tenant_slug: str | None = Query(default=None, min_length=1, max_length=100),
    db: Session = Depends(get_db),
):
    from fastapi import HTTPException
    from app.models.product import Product
    tenant = resolve_storefront_tenant(db, tenant_slug)
    product = db.query(Product).filter(
        Product.public_id == public_id,
        Product.tenant_id == tenant.id,
        Product.is_active.is_(True),
    ).first()
    if product is None:
        raise HTTPException(status_code=404, detail="Producto no disponible en esta empresa")
    return {"id": product.id, "public_id": str(product.public_id)}


# =========================================================
# CU26 - CONSULTAR DISPONIBILIDAD POR SUCURSAL
# =========================================================

@router.get(
    "/{product_id}/availability",

    response_model=
        CustomerProductAvailabilityResponse,
)
def get_customer_product_availability(

    product_id: int = Path(
        ...,
        ge=1,
    ),

    variant_id: int = Query(
        ...,
        ge=1,
    ),

    # =====================================================
    # CIUDAD OPCIONAL
    # =====================================================

    city_id: int | None = Query(
        default=None,
        ge=1,
    ),

    db: Session = Depends(
        get_db
    ),
    tenant_slug: str | None = Query(default=None, min_length=1, max_length=100),
):

    return (
        CustomerProductDetailService
        .get_variant_availability(
            db=db,

            product_id=
                product_id,

            variant_id=
                variant_id,

            city_id=
                city_id,

            tenant_id=resolve_storefront_tenant(db, tenant_slug).id,
        )
    )


# =========================================================
# CU26 - CONSULTAR DETALLE DE PRENDA
# =========================================================

@router.get(
    "/{product_id}",

    response_model=
        CustomerProductDetailResponse,
)
def get_customer_product_detail(

    product_id: int = Path(
        ...,
        ge=1,
    ),

    # =====================================================
    # SUCURSAL OPCIONAL
    # =====================================================

    branch_id: int | None = Query(
        default=None,
        ge=1,
    ),

    db: Session = Depends(
        get_db
    ),
    tenant_slug: str | None = Query(default=None, min_length=1, max_length=100),
):

    return (
        CustomerProductDetailService
        .get_product_detail(
            db=db,

            product_id=
                product_id,

            branch_id=
                branch_id,

            tenant_id=resolve_storefront_tenant(db, tenant_slug).id,
        )
    )