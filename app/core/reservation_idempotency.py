"""Fingerprint estable de reservas offline para reintentos idempotentes."""
import hashlib
import json


def reservation_operation_fingerprint(*, branch_id: int, customer_id: int, items, notes: str | None) -> str:
    """Equivalencia por sucursal, usuario, cantidades, variantes y notas."""
    totals: dict[int, int] = {}
    for item in items:
        variant_id = int(item.product_variant_id)
        totals[variant_id] = totals.get(variant_id, 0) + int(item.quantity)
    payload = {
        "branch_id": branch_id,
        "customer_id": customer_id,
        "items": sorted(totals.items()),
        "notes": notes or "",
    }
    return hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
