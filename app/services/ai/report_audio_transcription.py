"""Speech-to-text usando la MISMA clave OpenAI que los comandos de texto."""
import asyncio
import json
from urllib import request, error
from uuid import uuid4
from app.core.config import settings

MAX_SECONDS = 35

def _transcribe(data: bytes, mime: str) -> str:
    if not settings.openai_api_key.strip():
        raise RuntimeError("OpenAI no está configurado en el servidor.")
    extension = {"audio/webm": "webm", "audio/mp4": "m4a", "audio/mpeg": "mp3", "audio/wav": "wav", "audio/ogg": "ogg"}[mime]
    boundary = "FashionVoice" + uuid4().hex
    def part(name: str, value: bytes, filename: str | None = None, content_type: str | None = None) -> bytes:
        header = f"--{boundary}\r\nContent-Disposition: form-data; name=\"{name}\""
        if filename:
            header += f"; filename=\"{filename}\""
        header += "\r\n"
        if content_type:
            header += f"Content-Type: {content_type}\r\n"
        return header.encode() + b"\r\n" + value + b"\r\n"
    body = (part("model", b"gpt-4o-mini-transcribe") + part("language", b"es") +
            part("file", data, f"report.{extension}", mime) + f"--{boundary}--\r\n".encode())
    req = request.Request(
        "https://api.openai.com/v1/audio/transcriptions", data=body, method="POST",
        headers={"Authorization": f"Bearer {settings.openai_api_key}",
                 "Content-Type": f"multipart/form-data; boundary={boundary}"},
    )
    try:
        with request.urlopen(req, timeout=min(60, max(15, settings.openai_timeout_seconds))) as resp:
            result = json.loads(resp.read(65536))
    except error.HTTPError as exc:
        # Nunca exponemos el cuerpo de errores del proveedor ni secretos al navegador.
        if exc.code == 429:
            raise RuntimeError("El servicio de transcripción alcanzó su límite de uso. Intenta más tarde.") from exc
        raise RuntimeError("No fue posible transcribir el audio con OpenAI.") from exc
    except (error.URLError, TimeoutError) as exc:
        raise RuntimeError("No se pudo conectar al servicio de transcripción.") from exc
    text = str(result.get("text") or "").strip()
    if not text:
        raise ValueError("No se reconocieron palabras en la grabación.")
    return text[:1000]

async def transcribe_report_audio(data: bytes, mime: str) -> str:
    return await asyncio.to_thread(_transcribe, data, mime)
