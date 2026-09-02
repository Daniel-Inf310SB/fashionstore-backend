from datetime import datetime

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from fastapi.responses import (
    StreamingResponse,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.dependencies.audit_logs import (
    require_audit_logs_view,
)

from app.models.user import (
    User,
)

from app.schemas.audit_log import (
    AuditLogListResponse,
    AuditLogResponse,
)

from app.services.audit_log_service import (
    AuditLogService,
)


router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
)


# =========================================================
# LISTAR BITÁCORA
# =========================================================

@router.get(
    "",
    response_model=
        AuditLogListResponse,
)
def list_audit_logs(
    page: int = Query(
        default=1,
        ge=1,
    ),

    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
    ),

    search: str | None = Query(
        default=None,
        max_length=150,
    ),

    user_id: int | None = Query(
        default=None,
        ge=1,
    ),

    action: str | None = Query(
        default=None,
        max_length=100,
    ),

    module: str | None = Query(
        default=None,
        max_length=100,
    ),

    entity_type: str | None = Query(
        default=None,
        max_length=100,
    ),

    entity_id: int | None = Query(
        default=None,
        ge=1,
    ),

    log_status: str | None = Query(
        default=None,
        alias="status",
        max_length=30,
    ),

    date_from:
        datetime | None = Query(
            default=None,
        ),

    date_to:
        datetime | None = Query(
            default=None,
        ),

    sort_by: str = Query(
        default="created_at",
        pattern=(
            r"^(id|created_at|action|module|status|"
            r"user_id|entity_type|entity_id)$"
        ),
    ),

    sort_order: str = Query(
        default="desc",
        pattern=r"^(asc|desc)$",
    ),

    db: Session = Depends(
        get_db
    ),

    _: User = Depends(
        require_audit_logs_view
    ),
):

    return (
        AuditLogService
        .list_audit_logs(
            db=db,

            page=
                page,

            page_size=
                page_size,

            search=
                search,

            user_id=
                user_id,

            action=
                action,

            module=
                module,

            entity_type=
                entity_type,

            entity_id=
                entity_id,

            status=
                log_status,

            date_from=
                date_from,

            date_to=
                date_to,

            sort_by=
                sort_by,

            sort_order=
                sort_order,
        )
    )


# =========================================================
# EXPORTAR BITÁCORA A EXCEL
# =========================================================

@router.get(
    "/export/excel",
)
def export_audit_logs_excel(
    search: str | None = Query(
        default=None,
        max_length=150,
    ),

    user_id: int | None = Query(
        default=None,
        ge=1,
    ),

    action: str | None = Query(
        default=None,
        max_length=100,
    ),

    module: str | None = Query(
        default=None,
        max_length=100,
    ),

    entity_type: str | None = Query(
        default=None,
        max_length=100,
    ),

    entity_id: int | None = Query(
        default=None,
        ge=1,
    ),

    log_status: str | None = Query(
        default=None,
        alias="status",
        max_length=30,
    ),

    date_from:
        datetime | None = Query(
            default=None,
        ),

    date_to:
        datetime | None = Query(
            default=None,
        ),

    sort_by: str = Query(
        default="created_at",
        pattern=(
            r"^(id|created_at|action|module|status|"
            r"user_id|entity_type|entity_id)$"
        ),
    ),

    sort_order: str = Query(
        default="desc",
        pattern=r"^(asc|desc)$",
    ),

    db: Session = Depends(
        get_db
    ),

    _: User = Depends(
        require_audit_logs_view
    ),
):

    file_stream = (
        AuditLogService
        .export_excel(
            db=db,

            search=
                search,

            user_id=
                user_id,

            action=
                action,

            module=
                module,

            entity_type=
                entity_type,

            entity_id=
                entity_id,

            status=
                log_status,

            date_from=
                date_from,

            date_to=
                date_to,

            sort_by=
                sort_by,

            sort_order=
                sort_order,
        )
    )


    filename = (
        "fashionstore_bitacora_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ".xlsx"
    )


    return StreamingResponse(
        file_stream,

        media_type=(
            "application/"
            "vnd.openxmlformats-officedocument."
            "spreadsheetml.sheet"
        ),

        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )


# =========================================================
# EXPORTAR BITÁCORA A PDF
# =========================================================

@router.get(
    "/export/pdf",
)
def export_audit_logs_pdf(
    search: str | None = Query(
        default=None,
        max_length=150,
    ),

    user_id: int | None = Query(
        default=None,
        ge=1,
    ),

    action: str | None = Query(
        default=None,
        max_length=100,
    ),

    module: str | None = Query(
        default=None,
        max_length=100,
    ),

    entity_type: str | None = Query(
        default=None,
        max_length=100,
    ),

    entity_id: int | None = Query(
        default=None,
        ge=1,
    ),

    log_status: str | None = Query(
        default=None,
        alias="status",
        max_length=30,
    ),

    date_from:
        datetime | None = Query(
            default=None,
        ),

    date_to:
        datetime | None = Query(
            default=None,
        ),

    sort_by: str = Query(
        default="created_at",
        pattern=(
            r"^(id|created_at|action|module|status|"
            r"user_id|entity_type|entity_id)$"
        ),
    ),

    sort_order: str = Query(
        default="desc",
        pattern=r"^(asc|desc)$",
    ),

    db: Session = Depends(
        get_db
    ),

    _: User = Depends(
        require_audit_logs_view
    ),
):

    file_stream = (
        AuditLogService
        .export_pdf(
            db=db,

            search=
                search,

            user_id=
                user_id,

            action=
                action,

            module=
                module,

            entity_type=
                entity_type,

            entity_id=
                entity_id,

            status=
                log_status,

            date_from=
                date_from,

            date_to=
                date_to,

            sort_by=
                sort_by,

            sort_order=
                sort_order,
        )
    )


    filename = (
        "fashionstore_bitacora_"
        f"{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        ".pdf"
    )


    return StreamingResponse(
        file_stream,

        media_type=
            "application/pdf",

        headers={
            "Content-Disposition":
                f'attachment; filename="{filename}"'
        },
    )


# =========================================================
# OBTENER DETALLE DE BITÁCORA
# IMPORTANTE:
# ESTA RUTA DEBE ESTAR DESPUÉS DE /export/*
# =========================================================

@router.get(
    "/{audit_log_id}",
    response_model=
        AuditLogResponse,
)
def get_audit_log(
    audit_log_id: int,

    db: Session = Depends(
        get_db
    ),

    _: User = Depends(
        require_audit_logs_view
    ),
):

    try:

        return (
            AuditLogService
            .get_audit_log(
                db=db,

                audit_log_id=
                    audit_log_id,
            )
        )

    except LookupError as error:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail=
                str(error),
        )