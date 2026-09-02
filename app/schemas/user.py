from datetime import (
    date,
    datetime,
)

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    field_validator,
)


# =========================================================
# ROLE SUMMARY
# =========================================================

class UserRoleSummary(BaseModel):
    id: int

    name: str

    description: str | None = None

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CREAR USUARIO
# =========================================================

class UserCreate(BaseModel):
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
    )

    first_name: str = Field(
        min_length=2,
        max_length=100,
    )

    last_name: str | None = Field(
        default=None,
        max_length=100,
    )

    email: str = Field(
        min_length=5,
        max_length=160,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    document_number: str | None = Field(
        default=None,
        max_length=50,
    )

    address: str | None = Field(
        default=None,
        max_length=255,
    )

    date_of_birth: date | None = None

    password: str = Field(
        min_length=8,
        max_length=128,
    )

    role_id: int

    is_active: bool = True

    is_verified: bool = True

    profile_completed: bool = True


    @field_validator("email")
    @classmethod
    def normalize_email(
        cls,
        value: str,
    ) -> str:

        normalized = (
            value
            .strip()
            .lower()
        )

        if (
            "@" not in normalized
            or "." not in normalized.split("@")[-1]
        ):
            raise ValueError(
                "El correo electrónico no es válido"
            )

        return normalized


    @field_validator(
        "username",
        "last_name",
        "phone",
        "document_number",
        "address",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(
        cls,
        value,
    ):

        if value is None:
            return None

        value = str(value).strip()

        return value or None


    @field_validator(
        "first_name",
        mode="before",
    )
    @classmethod
    def normalize_required_name(
        cls,
        value,
    ) -> str:

        return str(value).strip()


# =========================================================
# ACTUALIZAR USUARIO
# =========================================================

class UserUpdate(BaseModel):
    username: str | None = Field(
        default=None,
        min_length=3,
        max_length=50,
    )

    first_name: str | None = Field(
        default=None,
        min_length=2,
        max_length=100,
    )

    last_name: str | None = Field(
        default=None,
        max_length=100,
    )

    email: str | None = Field(
        default=None,
        min_length=5,
        max_length=160,
    )

    phone: str | None = Field(
        default=None,
        max_length=30,
    )

    document_number: str | None = Field(
        default=None,
        max_length=50,
    )

    address: str | None = Field(
        default=None,
        max_length=255,
    )

    date_of_birth: date | None = None

    password: str | None = Field(
        default=None,
        min_length=8,
        max_length=128,
    )

    role_id: int | None = None

    is_active: bool | None = None

    is_verified: bool | None = None

    profile_completed: bool | None = None


    @field_validator("email")
    @classmethod
    def normalize_email(
        cls,
        value: str | None,
    ) -> str | None:

        if value is None:
            return None

        normalized = (
            value
            .strip()
            .lower()
        )

        if (
            "@" not in normalized
            or "." not in normalized.split("@")[-1]
        ):
            raise ValueError(
                "El correo electrónico no es válido"
            )

        return normalized


    @field_validator(
        "username",
        "first_name",
        "last_name",
        "phone",
        "document_number",
        "address",
        mode="before",
    )
    @classmethod
    def normalize_strings(
        cls,
        value,
    ):

        if value is None:
            return None

        value = str(value).strip()

        return value or None


# =========================================================
# RESPONSE
# =========================================================

class UserResponse(BaseModel):
    id: int

    username: str | None

    first_name: str

    last_name: str | None

    email: str

    phone: str | None

    document_number: str | None

    address: str | None

    date_of_birth: date | None

    photo_url: str | None

    role_id: int

    role: UserRoleSummary

    is_active: bool

    is_verified: bool

    profile_completed: bool

    last_login_at: datetime | None

    created_at: datetime

    updated_at: datetime

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# PAGINACIÓN
# =========================================================

class UserListResponse(BaseModel):
    items: list[UserResponse]

    page: int

    page_size: int

    total: int

    total_pages: int