from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


InventoryMovementType = Literal[
    "ENTRY",
    "SALE",
    "ADJUSTMENT_IN",
    "ADJUSTMENT_OUT",
    "RETURN_IN",
    "RETURN_OUT",
    "RESERVE",
    "RELEASE",
    "TRANSFER_IN",
    "TRANSFER_OUT",
]


# =========================================================
# SUCURSAL
# =========================================================

class InventoryMovementBranchSummary(BaseModel):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# PRODUCTO
# =========================================================

class InventoryMovementProductSummary(BaseModel):
    id: int

    code: str

    name: str

    brand: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# TALLA
# =========================================================

class InventoryMovementSizeSummary(BaseModel):
    id: int

    name: str

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# COLOR
# =========================================================

class InventoryMovementColorSummary(BaseModel):
    id: int

    name: str

    hex_code: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# VARIANTE
# =========================================================

class InventoryMovementVariantSummary(BaseModel):
    id: int

    product_id: int

    sku: str

    size: InventoryMovementSizeSummary

    color: InventoryMovementColorSummary

    product: InventoryMovementProductSummary

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# INVENTARIO
# =========================================================

class InventoryMovementInventorySummary(BaseModel):
    id: int

    branch_id: int

    product_variant_id: int

    branch: InventoryMovementBranchSummary

    product_variant: InventoryMovementVariantSummary

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# PROVEEDOR
# =========================================================

class InventoryMovementSupplierSummary(BaseModel):
    id: int

    name: str

    business_name: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# USUARIO
# =========================================================

class InventoryMovementUserSummary(BaseModel):
    id: int

    username: str | None = None

    first_name: str | None = None

    last_name: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CREATE
# =========================================================

class InventoryMovementCreate(BaseModel):
    inventory_id: int = Field(
        gt=0,
    )

    movement_type: InventoryMovementType

    quantity: int = Field(
        gt=0,
    )

    # Para ENTRY se selecciona la disponibilidad concreta
    # del proveedor para la variante del inventario.
    supplier_availability_id: int | None = Field(
        default=None,
        gt=0,
    )

    # Se conserva para otros movimientos donde pueda existir
    # un proveedor asociado. En ENTRY el backend lo deriva.
    supplier_id: int | None = Field(
        default=None,
        gt=0,
    )

    # En ENTRY el backend obtiene automáticamente el precio
    # efectivo desde SupplierAvailability/SupplierProduct.
    unit_cost: Decimal | None = Field(
        default=None,
        ge=0,
        max_digits=12,
        decimal_places=2,
    )

    reference_type: str | None = Field(
        default=None,
        max_length=50,
    )

    reference_id: int | None = Field(
        default=None,
        gt=0,
    )

    reference_code: str | None = Field(
        default=None,
        max_length=100,
    )

    reason: str | None = Field(
        default=None,
        max_length=255,
    )

    notes: str | None = None


# =========================================================
# RESPONSE
# =========================================================

class InventoryMovementResponse(BaseModel):
    id: int

    inventory_id: int

    movement_type: InventoryMovementType

    quantity: int

    stock_before: int

    stock_after: int

    reserved_before: int

    reserved_after: int

    supplier_id: int | None

    user_id: int | None

    unit_cost: Decimal | None

    reference_type: str | None

    reference_id: int | None

    reference_code: str | None

    reason: str | None

    notes: str | None

    created_at: datetime

    inventory: InventoryMovementInventorySummary

    supplier: InventoryMovementSupplierSummary | None

    user: InventoryMovementUserSummary | None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST RESPONSE
# =========================================================

class InventoryMovementListResponse(BaseModel):
    items: list[
        InventoryMovementResponse
    ]

    page: int

    page_size: int

    total: int

    total_pages: int