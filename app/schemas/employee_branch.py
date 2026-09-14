from datetime import datetime

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
)


# =========================================================
# ROLE SUMMARY
# =========================================================

class EmployeeRoleSummary(BaseModel):
    id: int

    name: str

    description: str | None

    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# EMPLOYEE SUMMARY
# =========================================================

class EmployeeSummary(BaseModel):
    id: int

    username: str | None

    first_name: str

    last_name: str | None

    email: str

    phone: str | None

    document_number: str | None

    photo_url: str | None

    role_id: int

    role: EmployeeRoleSummary

    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# CITY SUMMARY
# =========================================================

class EmployeeBranchCitySummary(BaseModel):
    id: int

    name: str

    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# BRANCH SUMMARY
# =========================================================

class EmployeeBranchBranchSummary(BaseModel):
    id: int

    name: str

    address: str

    city_id: int

    city: EmployeeBranchCitySummary

    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# ASIGNAR EMPLEADO
# =========================================================

class EmployeeBranchCreate(BaseModel):
    user_id: int = Field(
        gt=0,
    )

    branch_id: int = Field(
        gt=0,
    )


# =========================================================
# REASIGNAR EMPLEADO
# =========================================================

class EmployeeBranchReassign(BaseModel):
    branch_id: int = Field(
        gt=0,
    )


# =========================================================
# RESPONSE
# =========================================================

class EmployeeBranchResponse(BaseModel):
    id: int

    user_id: int

    branch_id: int

    assigned_at: datetime

    ended_at: datetime | None

    is_active: bool

    user: EmployeeSummary

    branch: EmployeeBranchBranchSummary

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LIST RESPONSE
# =========================================================

class EmployeeBranchListResponse(BaseModel):
    items: list[EmployeeBranchResponse]

    page: int

    page_size: int

    total: int

    total_pages: int


# =========================================================
# EMPLEADO DISPONIBLE
# =========================================================

class AvailableEmployeeResponse(BaseModel):
    id: int

    username: str | None

    first_name: str

    last_name: str | None

    email: str

    phone: str | None

    document_number: str | None

    photo_url: str | None

    role_id: int

    role: EmployeeRoleSummary

    is_active: bool

    model_config = ConfigDict(
        from_attributes=True,
    )


# =========================================================
# LISTA EMPLEADOS DISPONIBLES
# =========================================================

class AvailableEmployeeListResponse(BaseModel):
    items: list[AvailableEmployeeResponse]

    page: int

    page_size: int

    total: int

    total_pages: int