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

from app.database.session import get_db

from app.dependencies.branches import (
    require_branches_manage,
)

from app.models.user import User

from app.schemas.branch import (
    BranchCreate,
    BranchListResponse,
    BranchResponse,
    BranchUpdate,
)

from app.services.branch_service import (
    BranchService,
)


router = APIRouter(
    prefix="/branches",
    tags=["Branches"],
)


# =========================================================
# LISTAR SUCURSALES
# =========================================================

@router.get(
    "",
    response_model=BranchListResponse,
)
def get_branches(
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
    city_id: int | None = Query(
        default=None,
        gt=0,
    ),
    is_active: bool | None = Query(
        default=None,
    ),
    sort_by: Literal[
        "id",
        "name",
        "city_id",
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
        require_branches_manage
    ),
):

    return BranchService.get_branches(
        db=db,
        page=page,
        page_size=page_size,
        search=search,
        city_id=city_id,
        is_active=is_active,
        sort_by=sort_by,
        sort_order=sort_order,
    )


# =========================================================
# CREAR SUCURSAL
# =========================================================

@router.post(
    "",
    response_model=BranchResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_branch(
    payload: BranchCreate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_branches_manage
    ),
):

    try:
        return BranchService.create_branch(
            db=db,
            payload=payload,
            user_id=current_user.id,
            ip_address=(
                request.client.host
                if request.client
                else None
            ),
            user_agent=request.headers.get(
                "user-agent"
            ),
        )

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# OBTENER SUCURSAL POR ID
# =========================================================

@router.get(
    "/{branch_id}",
    response_model=BranchResponse,
)
def get_branch(
    branch_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_branches_manage
    ),
):

    try:
        return BranchService.get_branch(
            db=db,
            branch_id=branch_id,
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# ACTUALIZAR SUCURSAL
# =========================================================

@router.patch(
    "/{branch_id}",
    response_model=BranchResponse,
)
def update_branch(
    branch_id: int,
    payload: BranchUpdate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_branches_manage
    ),
):

    try:
        return BranchService.update_branch(
            db=db,
            branch_id=branch_id,
            payload=payload,
            user_id=current_user.id,
            ip_address=(
                request.client.host
                if request.client
                else None
            ),
            user_agent=request.headers.get(
                "user-agent"
            ),
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc


# =========================================================
# DESACTIVAR SUCURSAL
# =========================================================

@router.delete(
    "/{branch_id}",
    response_model=BranchResponse,
)
def deactivate_branch(
    branch_id: int,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_branches_manage
    ),
):

    try:
        return BranchService.deactivate_branch(
            db=db,
            branch_id=branch_id,
            user_id=current_user.id,
            ip_address=(
                request.client.host
                if request.client
                else None
            ),
            user_agent=request.headers.get(
                "user-agent"
            ),
        )

    except LookupError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc

    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc