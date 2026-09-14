from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


# =========================================================
# BASE
# =========================================================

class ColorBase(BaseModel):
    name: str = Field(
        min_length=1,
        max_length=50,
    )

    hex_code: str | None = Field(
        default=None,
        max_length=7,
    )

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    @field_validator(
        "hex_code"
    )
    @classmethod
    def validate_hex_code(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if value == "":
            return None

        if not value.startswith("#"):
            raise ValueError(
                "El código HEX debe comenzar con #."
            )

        if len(value) != 7:
            raise ValueError(
                "El código HEX debe tener el formato #RRGGBB."
            )

        hex_part = value[1:]

        valid_chars = (
            "0123456789"
            "abcdef"
            "ABCDEF"
        )

        if not all(
            char in valid_chars
            for char in hex_part
        ):
            raise ValueError(
                "El código HEX contiene caracteres inválidos."
            )

        return value.upper()


# =========================================================
# CREATE
# =========================================================

class ColorCreate(ColorBase):
    pass


# =========================================================
# UPDATE
# =========================================================

class ColorUpdate(BaseModel):
    name: str | None = Field(
        default=None,
        min_length=1,
        max_length=50,
    )

    hex_code: str | None = Field(
        default=None,
        max_length=7,
    )

    is_active: bool | None = None

    model_config = ConfigDict(
        str_strip_whitespace=True,
    )

    @field_validator(
        "hex_code"
    )
    @classmethod
    def validate_hex_code(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        value = value.strip()

        if value == "":
            return None

        if not value.startswith("#"):
            raise ValueError(
                "El código HEX debe comenzar con #."
            )

        if len(value) != 7:
            raise ValueError(
                "El código HEX debe tener el formato #RRGGBB."
            )

        hex_part = value[1:]

        valid_chars = (
            "0123456789"
            "abcdef"
            "ABCDEF"
        )

        if not all(
            char in valid_chars
            for char in hex_part
        ):
            raise ValueError(
                "El código HEX contiene caracteres inválidos."
            )

        return value.upper()


# =========================================================
# RESPONSE
# =========================================================

class ColorResponse(BaseModel):
    id: int

    name: str

    hex_code: str | None

    is_active: bool

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST RESPONSE
# =========================================================

class ColorListResponse(BaseModel):
    items: list[ColorResponse]

    page: int

    page_size: int

    total: int

    total_pages: int