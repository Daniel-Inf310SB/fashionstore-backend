from typing import Literal

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    Request,
    status,
)

from sqlalchemy.orm import Session

from app.database.session import (
    get_db,
)

from app.dependencies.suppliers import (
    require_suppliers_manage,
)

from app.models.user import User

from app.schemas.supplier import (
    SupplierCreate,
    SupplierListResponse,
    SupplierResponse,
    SupplierUpdate,
)

from app.services.suppliers import (
    SupplierService,
)


router = APIRouter(
    prefix="/suppliers",
    tags=["Suppliers"],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        SupplierListResponse,
)
def get_suppliers(
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
    ),
    is_active: bool | None = Query(
        default=None,
    ),
    sort_by: Literal[
        "id",
        "name",
        "business_name",
        "nit",
        "email",
        "is_active",
        "created_at",
        "updated_at",
    ] = Query(
        default="name",
    ),
    sort_order: Literal[
        "asc",
        "desc",
    ] = Query(
        default="asc",
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_suppliers_manage
    ),
):

    return (
        SupplierService
        .get_suppliers(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            is_active=is_active,
            sort_by=sort_by,
            sort_order=sort_order,
        )
    )


# =========================================================
# CREAR
# =========================================================

@router.post(
    "",
    response_model=
        SupplierResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def create_supplier(
    payload: SupplierCreate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_suppliers_manage
    ),
):

    try:

        return (
            SupplierService
            .create_supplier(
                db=db,
                payload=payload,
                user_id=
                    current_user.id,
                ip_address=(
                    request.client.host
                    if request.client
                    else None
                ),
                user_agent=
                    request.headers.get(
                        "user-agent"
                    ),
            )
        )

    except ValueError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# OBTENER
# =========================================================

@router.get(
    "/{supplier_id}",
    response_model=
        SupplierResponse,
)
def get_supplier(
    supplier_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_suppliers_manage
    ),
):

    try:

        return (
            SupplierService
            .get_supplier(
                db=db,
                supplier_id=
                    supplier_id,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# ACTUALIZAR
# =========================================================

@router.patch(
    "/{supplier_id}",
    response_model=
        SupplierResponse,
)
def update_supplier(
    supplier_id: int,
    payload: SupplierUpdate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_suppliers_manage
    ),
):

    try:

        return (
            SupplierService
            .update_supplier(
                db=db,
                supplier_id=
                    supplier_id,
                payload=payload,
                user_id=
                    current_user.id,
                ip_address=(
                    request.client.host
                    if request.client
                    else None
                ),
                user_agent=
                    request.headers.get(
                        "user-agent"
                    ),
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# DESACTIVAR
# =========================================================

@router.delete(
    "/{supplier_id}",
    response_model=
        SupplierResponse,
)
def deactivate_supplier(
    supplier_id: int,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_suppliers_manage
    ),
):

    try:

        return (
            SupplierService
            .deactivate_supplier(
                db=db,
                supplier_id=
                    supplier_id,
                user_id=
                    current_user.id,
                ip_address=(
                    request.client.host
                    if request.client
                    else None
                ),
                user_agent=
                    request.headers.get(
                        "user-agent"
                    ),
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
