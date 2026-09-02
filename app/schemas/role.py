from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)

from app.schemas.permission import PermissionSummary


# =========================================================
# CREAR ROL
# =========================================================

class RoleCreate(BaseModel):
    name: str = Field(
        min_length=2,
        max_length=50,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    permission_ids: list[int] = Field(
        default_factory=list,
    )


# =========================================================
# ACTUALIZAR ROL
# =========================================================

class RoleUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=2,
        max_length=50,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    is_active: bool | None = None


# =========================================================
# ASIGNAR PERMISOS
# =========================================================

class RolePermissionsUpdate(BaseModel):
    permission_ids: list[int] = Field(
        default_factory=list,
    )


# =========================================================
# RESPUESTA
# =========================================================

class RoleResponse(BaseModel):
    id: int

    name: str

    description: str | None

    is_active: bool

    permissions: list[PermissionSummary]

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LISTADO PAGINADO
# =========================================================

class RoleListResponse(BaseModel):
    items: list[RoleResponse]

    page: int

    page_size: int

    total: int

    total_pages: int