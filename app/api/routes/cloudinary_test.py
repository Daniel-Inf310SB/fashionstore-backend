from fastapi import (
    APIRouter,
    File,
    HTTPException,
    UploadFile,
)

from app.services.cloudinary_service import (
    CloudinaryService,
)


router = APIRouter(
    prefix="/test",
    tags=["Cloudinary Test"],
)


# =========================================================
# CONFIGURACIÓN
# =========================================================

ALLOWED_CONTENT_TYPES = {
    "image/jpeg",
    "image/png",
    "image/webp",
}

MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB


# =========================================================
# SUBIR IMAGEN
# =========================================================

@router.post(
    "/cloudinary-upload",
)
async def upload_cloudinary_test(
    file: UploadFile = File(...),
):

    # =====================================================
    # VALIDAR TIPO
    # =====================================================

    if file.content_type not in ALLOWED_CONTENT_TYPES:

        raise HTTPException(
            status_code=400,
            detail=(
                "Formato no permitido. "
                "Solo se permiten JPG, PNG y WEBP."
            ),
        )

    # =====================================================
    # LEER ARCHIVO
    # =====================================================

    content = await file.read()

    # =====================================================
    # VALIDAR TAMAÑO
    # =====================================================

    if len(content) > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=400,
            detail=(
                "La imagen supera el tamaño máximo "
                "permitido de 5 MB."
            ),
        )

    # Volver al inicio del archivo
    await file.seek(0)

    # =====================================================
    # SUBIR A CLOUDINARY
    # =====================================================

    try:

        result = CloudinaryService.upload_image(
            file=file.file,
            folder="fashionstore/test",
        )

        return {
            "message":
                "Imagen subida correctamente.",

            "image":
                result,
        }

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "No se pudo subir la imagen "
                "a Cloudinary."
            ),
        ) from exc