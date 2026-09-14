from decimal import Decimal
from io import BytesIO
from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.dependencies.products import (
    require_products_manage,
    require_products_view,
)

from app.models.user import User

from app.schemas.product import (
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)

from app.services.cloudinary_service import (
    CloudinaryService,
)

from app.services.product_service import (
    ProductService,
)


router = APIRouter(
    prefix="/products",
    tags=["Products"],
)


# =========================================================
# IMÁGENES
# =========================================================

ALLOWED_IMAGE_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_IMAGE_SIZE = (
    5 * 1024 * 1024
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        ProductListResponse,
)
def get_products(
    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
    ),

    search: str | None = Query(
        default=None,
    ),

    category_id: int | None = Query(
        default=None,
        gt=0,
    ),

    audience_id: int | None = Query(
        default=None,
        gt=0,
    ),

    brand: str | None = Query(
        default=None,
    ),

    is_active: bool | None = Query(
        default=None,
    ),

    price_from: Decimal | None = Query(
        default=None,
        ge=0,
    ),

    price_to: Decimal | None = Query(
        default=None,
        ge=0,
    ),

    sort_by: Literal[
        "id",
        "code",
        "name",
        "brand",
        "base_price",
        "is_active",
        "created_at",
        "updated_at",
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

    current_user: User = Depends(
        require_products_view
    ),
):

    if (
        price_from is not None
        and
        price_to is not None
        and
        price_to < price_from
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "El precio máximo no puede "
                "ser menor al precio mínimo."
            ),
        )

    return (
        ProductService
        .get_products(
            db=db,

            page=page,

            page_size=
                page_size,

            search=
                search,

            category_id=
                category_id,

            audience_id=
                audience_id,

            brand=
                brand,

            is_active=
                is_active,

            price_from=
                price_from,

            price_to=
                price_to,

            sort_by=
                sort_by,

            sort_order=
                sort_order,
        )
    )


# =========================================================
# CREAR
# =========================================================

@router.post(
    "",
    response_model=
        ProductResponse,

    status_code=
        status.HTTP_201_CREATED,
)
def create_product(
    payload:
        ProductCreate,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    try:

        return (
            ProductService
            .create_product(
                db=db,

                payload=
                    payload,

                user_id=
                    current_user.id,

                ip_address=(
                    request.client.host
                    if request.client
                    else None
                ),

                user_agent=
                    request.headers.get(
                        "user-agent"
                    ),
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# =========================================================
# OBTENER
# =========================================================

@router.get(
    "/{product_id}",
    response_model=
        ProductResponse,
)
def get_product(
    product_id:
        int,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_view
    ),
):

    try:

        return (
            ProductService
            .get_product(
                db=db,

                product_id=
                    product_id,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# =========================================================
# ACTUALIZAR
# =========================================================

@router.patch(
    "/{product_id}",
    response_model=
        ProductResponse,
)
def update_product(
    product_id:
        int,

    payload:
        ProductUpdate,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    try:

        return (
            ProductService
            .update_product(
                db=db,

                product_id=
                    product_id,

                payload=
                    payload,

                user_id=
                    current_user.id,

                ip_address=(
                    request.client.host
                    if request.client
                    else None
                ),

                user_agent=
                    request.headers.get(
                        "user-agent"
                    ),
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# =========================================================
# DESACTIVAR
# =========================================================

@router.delete(
    "/{product_id}",
    response_model=
        ProductResponse,
)
def deactivate_product(
    product_id:
        int,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    try:

        return (
            ProductService
            .deactivate_product(
                db=db,

                product_id=
                    product_id,

                user_id=
                    current_user.id,

                ip_address=(
                    request.client.host
                    if request.client
                    else None
                ),

                user_agent=
                    request.headers.get(
                        "user-agent"
                    ),
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


# =========================================================
# SUBIR / REEMPLAZAR PORTADA
# =========================================================

@router.post(
    "/{product_id}/cover",
    response_model=
        ProductResponse,
)
async def upload_product_cover(
    product_id:
        int,

    request:
        Request,

    file: UploadFile = File(...),

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    # =====================================================
    # PRODUCTO
    # =====================================================

    try:

        product = (
            ProductService
            .get_product(
                db=db,
                product_id=
                    product_id,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


    # =====================================================
    # TIPO
    # =====================================================

    if (
        file.content_type
        not in ALLOWED_IMAGE_TYPES
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Formato no permitido. "
                "Solo se permiten JPG, PNG "
                "y WEBP."
            ),
        )


    # =====================================================
    # TAMAÑO
    # =====================================================

    content = await file.read()

    if len(content) > MAX_IMAGE_SIZE:

        raise HTTPException(
            status_code=400,
            detail=(
                "La imagen supera el máximo "
                "permitido de 5 MB."
            ),
        )

    if len(content) == 0:

        raise HTTPException(
            status_code=400,
            detail=(
                "El archivo está vacío."
            ),
        )


    # =====================================================
    # GUARDAR PORTADA ANTERIOR
    # =====================================================

    old_public_id = (
        product.cover_image_public_id
    )


    # =====================================================
    # CLOUDINARY
    # =====================================================

    try:

        uploaded = (
            CloudinaryService
            .upload_image(
                file=BytesIO(
                    content
                ),
                folder=(
                    "fashionstore/products/"
                    f"{product_id}/cover"
                ),
            )
        )

    except Exception as exc:

        raise HTTPException(
            status_code=502,
            detail=(
                "No se pudo subir la imagen "
                "a Cloudinary."
            ),
        ) from exc


    # =====================================================
    # GUARDAR EN BD
    # =====================================================

    try:

        updated_product = (
            ProductService
            .update_cover(
                db=db,

                product_id=
                    product_id,

                image_url=
                    uploaded[
                        "url"
                    ],

                public_id=
                    uploaded[
                        "public_id"
                    ],

                user_id=
                    current_user.id,

                ip_address=(
                    request.client.host
                    if request.client
                    else None
                ),

                user_agent=
                    request.headers.get(
                        "user-agent"
                    ),
            )
        )

    except Exception as exc:

        # Si BD falla, no dejamos
        # archivo huérfano nuevo.

        try:
            CloudinaryService.delete_image(
                uploaded[
                    "public_id"
                ]
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=(
                "La imagen fue subida, "
                "pero no se pudo asociar "
                "al producto."
            ),
        ) from exc


    # =====================================================
    # BORRAR PORTADA ANTERIOR
    # =====================================================

    if (
        old_public_id
        and
        old_public_id
        != uploaded["public_id"]
    ):

        try:

            CloudinaryService.delete_image(
                old_public_id
            )

        except Exception:

            # No rompemos la actualización
            # porque la portada nueva ya quedó
            # correctamente guardada.
            pass


    return updated_product


# =========================================================
# ELIMINAR PORTADA
# =========================================================

@router.delete(
    "/{product_id}/cover",
    response_model=
        ProductResponse,
)
def delete_product_cover(
    product_id:
        int,

    request:
        Request,

    db: Session = Depends(
        get_db
    ),

    current_user: User = Depends(
        require_products_manage
    ),
):

    try:

        product = (
            ProductService
            .get_product(
                db=db,
                product_id=
                    product_id,
            )
        )

        old_public_id = (
            product.cover_image_public_id
        )

        updated_product = (
            ProductService
            .remove_cover(
                db=db,

                product_id=
                    product_id,

                user_id=
                    current_user.id,

                ip_address=(
                    request.client.host
                    if request.client
                    else None
                ),

                user_agent=
                    request.headers.get(
                        "user-agent"
                    ),
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc


    # =====================================================
    # CLOUDINARY
    # =====================================================

    if old_public_id:

        try:

            CloudinaryService.delete_image(
                old_public_id
            )

        except Exception:

            # La asociación ya fue eliminada
            # correctamente de PostgreSQL.
            pass


    return updated_product