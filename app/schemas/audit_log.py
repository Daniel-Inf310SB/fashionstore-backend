from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import (
    BaseModel,
    ConfigDict,
)


# =========================================================
# USUARIO RESUMIDO
# =========================================================

class AuditUserSummary(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    username: str | None = None

    first_name: str

    last_name: str | None = None

    email: str


# =========================================================
# RESPONSE
# =========================================================

class AuditLogResponse(BaseModel):

    model_config = ConfigDict(
        from_attributes=True,
    )

    id: int

    user_id: int | None = None

    action: str

    module: str

    entity_type: str | None = None

    entity_id: int | None = None

    description: str | None = None

    old_values:dict[str, Any] | None = None

    new_values:dict[str, Any] | None = None

    ip_address: str | None = None

    user_agent: str | None = None

    status: str

    created_at: datetime

    user:AuditUserSummary | None = None


# =========================================================
# LIST RESPONSE
# =========================================================

class AuditLogListResponse(BaseModel):

    items:list[AuditLogResponse]

    page:int

    page_size:int

    total:int

    total_pages:int