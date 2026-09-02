from datetime import date

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    Field,
)


# =========================
# REGISTRO
# =========================

class RegisterRequest(BaseModel):
    first_name: str = Field(
        min_length=2,
        max_length=100,
    )

    last_name: str | None = Field(
        default=None,
        max_length=100,
    )

    email: EmailStr

    password: str = Field(
        min_length=8,
        max_length=128,
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


class RegisterResponse(BaseModel):
    message: str
    email: EmailStr


# =========================
# VERIFICACIÓN EMAIL
# =========================

class VerifyEmailRequest(BaseModel):
    email: EmailStr

    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )


class ResendVerificationCodeRequest(BaseModel):
    email: EmailStr


class MessageResponse(BaseModel):
    message: str


# =========================
# LOGIN
# =========================

class LoginRequest(BaseModel):
    email: EmailStr

    password: str = Field(
        min_length=1,
        max_length=128,
    )

    device_id: str | None = None
    device_name: str | None = None
    platform: str | None = None


# =========================
# GOOGLE
# =========================

class GoogleLoginRequest(BaseModel):
    id_token: str

    device_id: str | None = None
    device_name: str | None = None
    platform: str | None = None


# =========================
# COMPLETAR PERFIL
# =========================

class CompleteProfileRequest(BaseModel):
    username: str = Field(
        min_length=3,
        max_length=50,
        pattern=r"^[a-zA-Z0-9._]+$",
    )

    date_of_birth: date

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

    photo_url: str | None = Field(
        default=None,
        max_length=500,
    )


class UsernameAvailabilityResponse(BaseModel):
    username: str
    available: bool
    suggestions: list[str]


# =========================
# REFRESH
# =========================

class RefreshTokenRequest(BaseModel):
    refresh_token: str


# =========================
# USUARIO
# =========================

class UserAuthResponse(BaseModel):
    id: int

    username: str | None

    first_name: str
    last_name: str | None

    email: EmailStr

    phone: str | None
    document_number: str | None
    address: str | None

    date_of_birth: date | None
    photo_url: str | None

    role: str

    permissions: list[str] = Field(
        default_factory=list,
    )

    is_active: bool
    is_verified: bool
    profile_completed: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================
# TOKENS
# =========================

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str

    token_type: str = "bearer"

    user: UserAuthResponse


# =========================
# LOGOUT
# =========================

class LogoutResponse(BaseModel):
    message: str


# =========================
# RECUPERAR CONTRASEÑA
# =========================

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyResetCodeRequest(BaseModel):
    email: EmailStr

    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )


class ResetPasswordRequest(BaseModel):
    email: EmailStr

    code: str = Field(
        min_length=6,
        max_length=6,
        pattern=r"^\d{6}$",
    )

    new_password: str = Field(
        min_length=8,
        max_length=128,
    )

class DocumentAvailabilityResponse(BaseModel):
    document_number: str
    available: bool