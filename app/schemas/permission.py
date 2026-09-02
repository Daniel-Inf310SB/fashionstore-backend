from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# RESUMEN
# =========================================================

class PermissionSummary(BaseModel):
    id: int

    code: str

    name: str

    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CREAR
# =========================================================

class PermissionCreate(BaseModel):
    code: str = Field(
        min_length=3,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$",
    )

    name: str = Field(
        min_length=2,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )


# =========================================================
# ACTUALIZAR
# =========================================================

class PermissionUpdate(BaseModel):
    code: str | None = Field(
        default=None,
        min_length=3,
        max_length=100,
        pattern=r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$",
    )

    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    is_active: bool | None = None


# =========================================================
# RESPUESTA
# =========================================================

class PermissionResponse(BaseModel):
    id: int

    code: str

    name: str

    description: str | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LISTADO PAGINADO
# =========================================================

class PermissionListResponse(BaseModel):
    items: list[PermissionResponse]

    page: int

    page_size: int

    total: int

    total_pages: int