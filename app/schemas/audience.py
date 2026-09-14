from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# BASE
# =========================================================

class AudienceBase(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=50,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# CREATE
# =========================================================

class AudienceCreate(AudienceBase):
    pass


# =========================================================
# UPDATE
# =========================================================

class AudienceUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    description: str | None = Field(
        default=None,
        max_length=255,
    )

    is_active: bool | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )


# =========================================================
# RESPONSE
# =========================================================

class AudienceResponse(BaseModel):
    id: int

    name: str

    description: str | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST RESPONSE
# =========================================================

class AudienceListResponse(BaseModel):
    items: list[AudienceResponse]

    page: int

    page_size: int

    total: int

    total_pages: int