from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.dependencies.products import (
    require_products_manage,
    require_products_view,
)

from app.models.user import User

from app.schemas.product_variant import (
    ProductVariantCreate,
    ProductVariantListResponse,
    ProductVariantResponse,
    ProductVariantUpdate,
)

from app.services.cloudinary_service import (
    CloudinaryService,
)

from app.services.product_variant_service import (
    ProductVariantService,
)


router = APIRouter(
    tags=["Product Variants"],
)


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
    "/products/{product_id}/variants",
    response_model=
        ProductVariantListResponse,
)
def get_product_variants(
    product_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_products_view
    ),
):

    try:
        items = (
            ProductVariantService
            .get_variants(
                db=db,
                product_id=product_id,
                include_inactive=
                    include_inactive,
            )
        )

        return {
            "items": items,
            "total": len(items),
        }

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc


# =========================================================
# CREAR
# =========================================================

@router.post(
    "/products/{product_id}/variants",
    response_model=
        ProductVariantResponse,
    status_code=201,
)
def create_product_variant(
    product_id: int,
    payload: ProductVariantCreate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_products_manage
    ),
):

    try:
        return (
            ProductVariantService
            .create_variant(
                db=db,
                product_id=product_id,
                payload=payload,
                user_id=current_user.id,
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
# ACTUALIZAR
# =========================================================

@router.patch(
    "/product-variants/{variant_id}",
    response_model=
        ProductVariantResponse,
)
def update_product_variant(
    variant_id: int,
    payload: ProductVariantUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_products_manage
    ),
):

    try:
        return (
            ProductVariantService
            .update_variant(
                db=db,
                variant_id=variant_id,
                payload=payload,
                user_id=current_user.id,
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
# SUBIR / REEMPLAZAR IMAGEN
# =========================================================

@router.post(
    "/product-variants/{variant_id}/image",
    response_model=
        ProductVariantResponse,
)
async def upload_variant_image(
    variant_id: int,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_products_manage
    ),
):

    try:
        variant = (
            ProductVariantService
            .get_variant(
                db=db,
                variant_id=variant_id,
            )
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    if (
        file.content_type
        not in ALLOWED_IMAGE_TYPES
    ):
        raise HTTPException(
            status_code=400,
            detail=(
                "Solo se permiten imágenes "
                "JPG, PNG y WEBP."
            ),
        )

    content = await file.read()

    if not content:
        raise HTTPException(
            status_code=400,
            detail="El archivo está vacío.",
        )

    if len(content) > MAX_IMAGE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=(
                "La imagen supera el máximo "
                "permitido de 5 MB."
            ),
        )

    old_public_id = (
        variant.cloudinary_public_id
    )

    try:
        uploaded = (
            CloudinaryService
            .upload_image(
                file=BytesIO(content),
                folder=(
                    "fashionstore/products/"
                    f"{variant.product_id}/"
                    f"variants/{variant.id}"
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

    try:
        updated = (
            ProductVariantService
            .update_image(
                db=db,
                variant_id=variant.id,
                image_url=
                    uploaded["url"],
                cloudinary_public_id=
                    uploaded["public_id"],
                user_id=current_user.id,
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

        try:
            CloudinaryService.delete_image(
                uploaded["public_id"]
            )
        except Exception:
            pass

        raise HTTPException(
            status_code=500,
            detail=(
                "La imagen fue subida, "
                "pero no pudo asociarse "
                "a la variante."
            ),
        ) from exc

    if (
        old_public_id
        and old_public_id
        != uploaded["public_id"]
    ):
        try:
            CloudinaryService.delete_image(
                old_public_id
            )
        except Exception:
            pass

    return updated