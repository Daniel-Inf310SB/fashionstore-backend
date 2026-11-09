"""Stable, backward-compatible codes for offline commercial errors.

The public JSON `detail` remains a string for existing Flutter clients.
Mobile clients can use X-FS-Error-Code and X-FS-Available-Quantity
rather than parsing Spanish error text. No stock quantity is invented.
"""
import re


def commercial_error_headers(error: Exception) -> dict[str, str]:
    message = str(error).lower()
    if isinstance(error, PermissionError):
        kind = "FORBIDDEN"
    elif any(x in message for x in ("uuid", "identificador de operación")):
        kind = "OPERATION_ID_CONFLICT"
    elif "pending" in message or "reserva pendiente" in message:
        kind = "EXISTING_PENDING_RESERVATION"
    elif "stock" in message or "unidades disponibles" in message or "inventario" in message:
        kind = "INSUFFICIENT_STOCK"
    elif "inactiva" in message or "desactivad" in message or "no está disponible" in message:
        kind = "VARIANT_UNAVAILABLE"
    elif isinstance(error, LookupError):
        kind = "NOT_FOUND"
    elif isinstance(error, ValueError):
        kind = "VALIDATION_ERROR"
    else:
        kind = "SERVER_ERROR"
    headers = {"X-FS-Error-Code": kind}
    if kind == "INSUFFICIENT_STOCK":
        match = re.search(r"solo hay (\d+) unidades disponibles", message)
        if match:
            headers["X-FS-Available-Quantity"] = match.group(1)
    return headers
