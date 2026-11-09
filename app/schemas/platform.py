from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field, field_validator

class TenantCreate(BaseModel):
    name: str = Field(min_length=2, max_length=150)
    slug: str = Field(min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    legal_name: str | None = Field(default=None, max_length=200)
    tax_id: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    logo_url: str | None = Field(default=None, max_length=500)

    @field_validator("name", "slug", mode="before")
    @classmethod
    def strip_required(cls, value):
        return value.strip() if isinstance(value, str) else value

class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=2, max_length=150)
    slug: str | None = Field(default=None, min_length=2, max_length=100, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    legal_name: str | None = Field(default=None, max_length=200)
    tax_id: str | None = Field(default=None, max_length=50)
    email: str | None = Field(default=None, max_length=255)
    phone: str | None = Field(default=None, max_length=30)
    logo_url: str | None = Field(default=None, max_length=500)

    @field_validator("name", "slug", mode="before")
    @classmethod
    def strip_required(cls, value):
        return value.strip() if isinstance(value, str) else value

class TenantStatusUpdate(BaseModel):
    is_active: bool

class TenantOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    slug: str
    legal_name: str | None
    tax_id: str | None
    email: str | None
    phone: str | None
    logo_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

class TenantAdminCreate(BaseModel):
    first_name: str = Field(min_length=2, max_length=100)
    last_name: str | None = Field(default=None, max_length=100)
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    username: str | None = Field(default=None, min_length=3, max_length=50)

    @field_validator("email")
    @classmethod
    def normalize_email(cls, value: str) -> str:
        email = value.strip().lower()
        if "@" not in email or "." not in email.split("@")[-1]:
            raise ValueError("Correo electrónico inválido")
        return email

class TenantAdminOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    first_name: str
    last_name: str | None
    email: str
    username: str | None
    tenant_id: int | None
    is_active: bool


class TenantOnboardCreate(BaseModel):
    tenant: TenantCreate
    admin: TenantAdminCreate


class TenantOnboardOut(BaseModel):
    tenant: TenantOut
    admin: TenantAdminOut
