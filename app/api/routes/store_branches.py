from fastapi import (
    APIRouter,
    Depends,
)

from sqlalchemy.orm import Session

from app.database.session import get_db

from app.schemas.branch import (
    BranchListResponse,
)

from app.services.branch_service import (
    BranchService,
)


router = APIRouter(
    prefix="/store/branches",
    tags=["Store - Branches"],
)


# =========================================================
# LISTAR SUCURSALES PÚBLICAS ACTIVAS
# =========================================================

@router.get(
    "",
    response_model=BranchListResponse,
)
def get_store_branches(
    db: Session = Depends(
        get_db
    ),
):

    return BranchService.get_branches(
        db=db,
        page=1,
        page_size=100,
        search=None,
        city_id=None,
        is_active=True,
        sort_by="name",
        sort_order="asc",
    )