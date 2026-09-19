from __future__ import annotations

import base64
from io import BytesIO
from urllib.parse import urlparse

from sqlalchemy.orm import Session, joinedload

from app.models.product_variant import ProductVariant
from app.services.ai.openai_service import OpenAIService
from app.services.ai.virtual_try_on_prompt import VirtualTryOnPrompt
from app.services.cloudinary_service import CloudinaryService


class VirtualTryOnService:
    ALLOWED_IMAGE_TYPES = {
        "image/jpeg",
        "image/png",
        "image/webp",
    }
    MAX_PERSON_IMAGE_BYTES = 10 * 1024 * 1024

    @staticmethod
    def _data_url(content: bytes, content_type: str) -> str:
        encoded = base64.b64encode(content).decode("ascii")
        return f"data:{content_type};base64,{encoded}"

    @staticmethod
    def _validate_garment_url(image_url: str | None) -> str:
        if not image_url or not image_url.strip():
            raise ValueError(
                "La variante no tiene una imagen propia. "
                "Sube la imagen de la variante antes de usar el probador virtual."
            )

        image_url = image_url.strip()
        parsed = urlparse(image_url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError(
                "La imagen de la variante debe estar disponible mediante una URL HTTP/HTTPS accesible."
            )

        return image_url

    @staticmethod
    def _detect_output_format(content: bytes) -> tuple[str, str]:
        if content.startswith(b"\x89PNG\r\n\x1a\n"):
            return "png", "image/png"
        if content.startswith(b"\xff\xd8\xff"):
            return "jpg", "image/jpeg"
        if len(content) >= 12 and content[:4] == b"RIFF" and content[8:12] == b"WEBP":
            return "webp", "image/webp"
        return "png", "image/png"

    @staticmethod
    def generate(
        db: Session,
        *,
        variant_id: int,
        person_image: bytes,
        person_content_type: str | None,
        user_id: int,
    ) -> dict:
        if not person_content_type or person_content_type not in VirtualTryOnService.ALLOWED_IMAGE_TYPES:
            raise ValueError("La foto de la persona debe ser JPG, PNG o WEBP.")

        if not person_image:
            raise ValueError("La foto de la persona está vacía.")

        if len(person_image) > VirtualTryOnService.MAX_PERSON_IMAGE_BYTES:
            raise ValueError("La foto de la persona supera el máximo permitido de 10 MB.")

        variant = (
            db.query(ProductVariant)
            .options(
                joinedload(ProductVariant.product),
                joinedload(ProductVariant.color),
                joinedload(ProductVariant.size),
            )
            .filter(ProductVariant.id == variant_id)
            .first()
        )

        if variant is None:
            raise LookupError("Variante no encontrada.")

        if not variant.is_active:
            raise ValueError("La variante seleccionada está desactivada.")

        product = variant.product
        if product is None or not product.is_active:
            raise ValueError("El producto de la variante no está disponible.")

        garment_image_url = VirtualTryOnService._validate_garment_url(variant.image_url)

        # El aspecto de la prenda se define EXCLUSIVAMENTE por la imagen de la variante.
        # No enviamos nombre, color, talla, categoría ni marca al prompt porque pueden
        # contradecir lo visible en la fotografía de referencia.
        prompt = VirtualTryOnPrompt.build()

        generated_bytes, usage = OpenAIService.generate_virtual_try_on(
            prompt=prompt,
            person_image_data_url=VirtualTryOnService._data_url(
                person_image,
                person_content_type,
            ),
            garment_image_url=garment_image_url,
        )

        if not generated_bytes:
            raise RuntimeError("OpenAI no devolvió una imagen generada.")

        output_format, output_content_type = VirtualTryOnService._detect_output_format(generated_bytes)

        try:
            uploaded = CloudinaryService.upload_image(
                file=BytesIO(generated_bytes),
                folder=f"fashionstore/virtual-try-on/users/{user_id}",
            )
        except Exception as exc:
            raise RuntimeError(
                "La imagen fue generada, pero no se pudo guardar el resultado en Cloudinary."
            ) from exc

        return {
            "message": "Prueba virtual generada correctamente.",
            "product_id": product.id,
            "variant_id": variant.id,
            "sku": variant.sku,
            "product_name": product.name,
            "color": variant.color.name,
            "size": variant.size.name,
            "garment_image_url": garment_image_url,
            "generated_image_url": uploaded["url"],
            "generated_image_public_id": uploaded["public_id"],
            "generated_image_width": uploaded.get("width"),
            "generated_image_height": uploaded.get("height"),
            "output_format": uploaded.get("format") or output_format,
            "output_content_type": output_content_type,
            "usage": usage,
        }
