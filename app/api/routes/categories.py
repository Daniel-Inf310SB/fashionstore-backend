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

from app.dependencies.categories import (
    require_categories_manage,
)

from app.models.user import User

from app.schemas.category import (
    CategoryCreate,
    CategoryListResponse,
    CategoryResponse,
    CategoryUpdate,
)

from app.services.category_service import (
    CategoryService,
)


router = APIRouter(
    prefix="/categories",
    tags=["Categories"],
)


# =========================================================
# LISTAR
# =========================================================

@router.get(
    "",
    response_model=
        CategoryListResponse,
)
def get_categories(
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
        require_categories_manage
    ),
):

    return (
        CategoryService
        .get_categories(
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
        CategoryResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def create_category(
    payload: CategoryCreate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_categories_manage
    ),
):

    try:

        return (
            CategoryService
            .create_category(
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
    "/{category_id}",
    response_model=
        CategoryResponse,
)
def get_category(
    category_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_categories_manage
    ),
):

    try:

        return (
            CategoryService
            .get_category(
                db=db,
                category_id=
                    category_id,
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
    "/{category_id}",
    response_model=
        CategoryResponse,
)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_categories_manage
    ),
):

    try:

        return (
            CategoryService
            .update_category(
                db=db,
                category_id=
                    category_id,
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
    "/{category_id}",
    response_model=
        CategoryResponse,
)
def deactivate_category(
    category_id: int,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_categories_manage
    ),
):

    try:

        return (
            CategoryService
            .deactivate_category(
                db=db,
                category_id=
                    category_id,
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