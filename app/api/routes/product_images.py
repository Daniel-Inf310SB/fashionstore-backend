from io import BytesIO

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
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

from app.schemas.product_image import (
    ProductImageListResponse,
    ProductImageResponse,
    ProductImageUpdate,
)

from app.services.cloudinary_service import (
    CloudinaryService,
)

from app.services.product_image_service import (
    ProductImageService,
)


router = APIRouter(
    tags=["Product Images"],
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
    "/products/{product_id}/images",
    response_model=
        ProductImageListResponse,
)
def get_product_images(
    product_id: int,
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_products_view
    ),
):

    try:
        items = (
            ProductImageService
            .get_images(
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
# SUBIR
# =========================================================

@router.post(
    "/products/{product_id}/images",
    response_model=
        ProductImageResponse,
    status_code=201,
)
async def upload_product_image(
    product_id: int,
    request: Request,

    file: UploadFile = File(...),

    alt_text: str | None = Form(
        default=None,
    ),

    sort_order: int = Form(
        default=0,
        ge=0,
    ),

    is_primary: bool = Form(
        default=False,
    ),

    db: Session = Depends(get_db),

    current_user: User = Depends(
        require_products_manage
    ),
):

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

    try:
        ProductImageService._get_product(
            db=db,
            product_id=product_id,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=404,
            detail=str(exc),
        ) from exc

    try:
        uploaded = (
            CloudinaryService
            .upload_image(
                file=BytesIO(content),
                folder=(
                    "fashionstore/products/"
                    f"{product_id}/gallery"
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
        return (
            ProductImageService
            .create_image(
                db=db,
                product_id=product_id,
                image_url=
                    uploaded["url"],
                cloudinary_public_id=
                    uploaded["public_id"],
                alt_text=alt_text,
                sort_order=sort_order,
                is_primary=is_primary,
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
                "pero no pudo registrarse "
                "en la base de datos."
            ),
        ) from exc


# =========================================================
# ACTUALIZAR
# =========================================================

@router.patch(
    "/product-images/{image_id}",
    response_model=
        ProductImageResponse,
)
def update_product_image(
    image_id: int,
    payload: ProductImageUpdate,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_products_manage
    ),
):

    try:
        return (
            ProductImageService
            .update_image(
                db=db,
                image_id=image_id,
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


# =========================================================
# ELIMINAR
# =========================================================

@router.delete(
    "/product-images/{image_id}",
)
def delete_product_image(
    image_id: int,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_products_manage
    ),
):

    try:
        public_id = (
            ProductImageService
            .delete_image(
                db=db,
                image_id=image_id,
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

    if public_id:
        try:
            CloudinaryService.delete_image(
                public_id
            )
        except Exception:
            pass

    return {
        "message":
            "Imagen eliminada correctamente."
    }