from __future__ import annotations

import base64
import binascii
import json
import time
from typing import Any
from urllib import error, request

from app.core.config import settings


class OpenAIService:
    API_URL = "https://api.openai.com/v1/responses"
    RETRYABLE_HTTP_CODES = {429, 500, 502, 503, 504}

    @staticmethod
    def _extract_text(payload: dict[str, Any]) -> str:
        direct = payload.get("output_text")
        if isinstance(direct, str) and direct.strip():
            return direct.strip()

        texts: list[str] = []

        for item in payload.get("output", []) or []:
            if not isinstance(item, dict):
                continue

            for content in item.get("content", []) or []:
                if not isinstance(content, dict):
                    continue

                text = content.get("text")
                if isinstance(text, str) and text.strip():
                    texts.append(text.strip())

        if not texts:
            raise RuntimeError("OpenAI no devolvió contenido de texto.")

        return "\n".join(texts)

    @staticmethod
    def _extract_usage(payload: dict[str, Any]) -> dict[str, int | None]:
        usage = payload.get("usage") or {}

        input_tokens = usage.get("input_tokens")
        output_tokens = usage.get("output_tokens")
        total_tokens = usage.get("total_tokens")

        if (
            total_tokens is None
            and isinstance(input_tokens, int)
            and isinstance(output_tokens, int)
        ):
            total_tokens = input_tokens + output_tokens

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    @staticmethod
    def _extract_generated_image(payload: dict[str, Any]) -> bytes:
        """
        Extrae la imagen base64 generada por la herramienta
        image_generation de Responses API.
        """

        for item in payload.get("output", []) or []:
            if not isinstance(item, dict):
                continue

            if item.get("type") != "image_generation_call":
                continue

            result = item.get("result")

            if not isinstance(result, str) or not result.strip():
                continue

            encoded = result.strip()

            if encoded.startswith("data:") and "," in encoded:
                encoded = encoded.split(",", 1)[1]

            try:
                return base64.b64decode(
                    encoded,
                    validate=True,
                )

            except (binascii.Error, ValueError) as exc:
                raise RuntimeError(
                    "OpenAI devolvió una imagen base64 inválida."
                ) from exc

        raise RuntimeError(
            "OpenAI no devolvió un resultado de generación de imagen."
        )

    @staticmethod
    def _request_payload(
        body: dict[str, Any],
        *,
        timeout_seconds: int | None = None,
    ) -> dict[str, Any]:

        attempts = max(
            1,
            settings.openai_max_retries + 1,
        )

        last_error: Exception | None = None

        timeout = (
            timeout_seconds
            or settings.openai_timeout_seconds
        )

        for attempt in range(attempts):

            req = request.Request(
                OpenAIService.API_URL,
                data=json.dumps(body).encode("utf-8"),
                headers={
                    "Authorization": (
                        f"Bearer {settings.openai_api_key}"
                    ),
                    "Content-Type": "application/json",
                },
                method="POST",
            )

            try:
                with request.urlopen(
                    req,
                    timeout=timeout,
                ) as response:
                    raw = response.read().decode("utf-8")

                payload = json.loads(raw)

                if not isinstance(payload, dict):
                    raise RuntimeError(
                        "OpenAI devolvió un formato HTTP inesperado."
                    )

                return payload

            except error.HTTPError as exc:

                detail = exc.read().decode(
                    "utf-8",
                    errors="replace",
                )

                last_error = RuntimeError(
                    f"OpenAI respondió HTTP {exc.code}: "
                    f"{detail[:800]}"
                )

                should_retry = (
                    exc.code
                    in OpenAIService.RETRYABLE_HTTP_CODES
                    and attempt < attempts - 1
                )

                if not should_retry:
                    raise last_error from exc

            except error.URLError as exc:

                last_error = RuntimeError(
                    f"No se pudo conectar con OpenAI: "
                    f"{exc.reason}"
                )

                if attempt >= attempts - 1:
                    raise last_error from exc

            except TimeoutError as exc:

                last_error = RuntimeError(
                    "La conexión con OpenAI excedió "
                    "el tiempo de espera."
                )

                if attempt >= attempts - 1:
                    raise last_error from exc

            time.sleep(
                settings.openai_retry_base_delay_seconds
                * (2**attempt)
            )

        raise (
            last_error
            or RuntimeError(
                "No se pudo completar la solicitud a OpenAI."
            )
        )

    @staticmethod
    def generate_json(
        *,
        instructions: str,
        input_data: dict[str, Any],
    ) -> tuple[
        dict[str, Any],
        dict[str, int | None],
    ]:

        if not settings.openai_api_key.strip():
            raise RuntimeError(
                "OPENAI_API_KEY no está configurada."
            )

        body = {
            "model": settings.openai_model,
            "instructions": instructions,
            "input": json.dumps(
                input_data,
                ensure_ascii=False,
                default=str,
            ),
            "max_output_tokens": (
                settings.openai_max_output_tokens
            ),
        }

        payload = OpenAIService._request_payload(body)

        text = OpenAIService._extract_text(payload)

        usage = OpenAIService._extract_usage(payload)

        clean = text.strip()

        if clean.startswith("```"):
            clean = clean.strip("`")

            if clean.lower().startswith("json"):
                clean = clean[4:].strip()

        try:
            parsed = json.loads(clean)

        except json.JSONDecodeError as exc:
            raise RuntimeError(
                "La IA devolvió una respuesta "
                "que no es JSON válido."
            ) from exc

        if not isinstance(parsed, dict):
            raise RuntimeError(
                "La IA devolvió un formato inesperado."
            )

        return parsed, usage

    @staticmethod
    def generate_virtual_try_on(
        *,
        prompt: str,
        person_image_data_url: str,
        garment_image_url: str,
    ) -> tuple[
        bytes,
        dict[str, int | None],
    ]:
        """
        Genera una prueba virtual 2D utilizando:

        IMAGE 1:
            Fotografía original de la persona.

        IMAGE 2:
            Imagen exacta de la variante seleccionada.

        La segunda imagen debe considerarse la única
        referencia visual válida de la prenda.
        """

        if not settings.openai_api_key.strip():
            raise RuntimeError(
                "OPENAI_API_KEY no está configurada."
            )

        model = (
            settings.openai_image_model.strip()
            or settings.openai_model
        )

        body = {
            "model": model,

            "input": [
                {
                    "role": "user",

                    "content": [
                        {
                            "type": "input_text",
                            "text": prompt,
                        },

                        # =====================================================
                        # IMAGEN 1 - PERSONA
                        # =====================================================
                        {
                            "type": "input_text",
                            "text": (
                                "IMAGE 1 — PERSON / BASE PHOTO.\n"
                                "\n"
                                "This is the original photograph that must "
                                "remain visually unchanged except for the "
                                "clothing region.\n"
                                "\n"
                                "Preserve exactly:\n"
                                "- identity\n"
                                "- face\n"
                                "- facial features\n"
                                "- hair\n"
                                "- skin tone\n"
                                "- body shape\n"
                                "- body proportions\n"
                                "- pose\n"
                                "- arms\n"
                                "- hands\n"
                                "- camera angle\n"
                                "- framing\n"
                                "- background\n"
                                "- lighting\n"
                                "- shadows\n"
                                "\n"
                                "Do not beautify, reshape, slim, enlarge, "
                                "retouch or reconstruct the person.\n"
                                "\n"
                                "Only replace the visible clothing area."
                            ),
                        },

                        {
                            "type": "input_image",
                            "image_url": person_image_data_url,
                        },

                        # =====================================================
                        # IMAGEN 2 - PRENDA
                        # =====================================================
                        {
                            "type": "input_text",
                            "text": (
                                "IMAGE 2 — EXACT GARMENT REFERENCE.\n"
                                "\n"
                                "THIS IMAGE IS THE ONLY SOURCE OF TRUTH "
                                "FOR THE GARMENT.\n"
                                "\n"
                                "Ignore product names, database colors, "
                                "sizes, categories, metadata and textual "
                                "descriptions.\n"
                                "\n"
                                "Study the garment directly from this image "
                                "and reproduce that same garment on the "
                                "person from IMAGE 1.\n"
                                "\n"
                                "Preserve all visible garment characteristics:\n"
                                "- garment type\n"
                                "- silhouette\n"
                                "- shape\n"
                                "- visible colors\n"
                                "- neckline\n"
                                "- sleeve presence or absence\n"
                                "- sleeve length\n"
                                "- straps\n"
                                "- collar\n"
                                "- buttons\n"
                                "- zipper\n"
                                "- seams\n"
                                "- printed graphics\n"
                                "- logos\n"
                                "- patterns\n"
                                "- textures\n"
                                "- visible construction details\n"
                                "- proportions\n"
                                "\n"
                                "DO NOT redesign the garment.\n"
                                "DO NOT substitute it with another garment.\n"
                                "DO NOT create a similar item.\n"
                                "DO NOT invent missing decorative details.\n"
                                "DO NOT add sleeves if none are visible.\n"
                                "DO NOT remove sleeves if they are visible.\n"
                                "DO NOT add a collar if none exists.\n"
                                "DO NOT create buttons unless they exist.\n"
                                "DO NOT replace the visible graphic.\n"
                                "DO NOT reinterpret the garment as a "
                                "different fashion item.\n"
                                "\n"
                                "The goal is garment transfer, "
                                "not fashion redesign."
                            ),
                        },

                        {
                            "type": "input_image",
                            "image_url": garment_image_url,
                        },
                    ],
                }
            ],

            # =============================================================
            # IMAGE GENERATION TOOL
            #
            # IMPORTANTE:
            # gpt-image-2 actualmente rechaza input_fidelity,
            # por eso NO debe enviarse dicho parámetro aquí.
            # =============================================================
            "tools": [
                {
                    "type": "image_generation",
                }
            ],

            "tool_choice": {
                "type": "image_generation",
            },
        }

        payload = OpenAIService._request_payload(
            body,
            timeout_seconds=(
                settings.openai_image_timeout_seconds
            ),
        )

        image_bytes = (
            OpenAIService._extract_generated_image(
                payload
            )
        )

        usage = OpenAIService._extract_usage(
            payload
        )

        return image_bytes, usage