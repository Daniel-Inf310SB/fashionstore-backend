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

from app.dependencies.employee_branches import (
    require_employee_branches_manage,
    require_employee_branches_view,
)

from app.models.user import User

from app.schemas.employee_branch import (
    AvailableEmployeeListResponse,
    EmployeeBranchCreate,
    EmployeeBranchListResponse,
    EmployeeBranchReassign,
    EmployeeBranchResponse,
)

from app.services.employee_branch_service import (
    EmployeeBranchService,
)


router = APIRouter(
    prefix="/branch-staff",
    tags=["Branch Staff"],
)


# =========================================================
# LISTAR PERSONAL
# =========================================================

@router.get(
    "",
    response_model=
        EmployeeBranchListResponse,
)
def get_assignments(
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
    branch_id: int | None = Query(
        default=None,
        gt=0,
    ),
    role_id: int | None = Query(
        default=None,
        gt=0,
    ),
    is_active: bool | None = Query(
        default=True,
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_employee_branches_manage
    ),
):

    return (
        EmployeeBranchService
        .get_assignments(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            branch_id=branch_id,
            role_id=role_id,
            is_active=is_active,
        )
    )


# =========================================================
# EMPLEADOS DISPONIBLES
#
# IMPORTANTE:
# Debe estar antes de /{assignment_id}
# =========================================================

@router.get(
    "/available",
    response_model=
        AvailableEmployeeListResponse,
)
def get_available_employees(
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
    role_id: int | None = Query(
        default=None,
        gt=0,
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_employee_branches_manage
    ),
):

    return (
        EmployeeBranchService
        .get_available_employees(
            db=db,
            page=page,
            page_size=page_size,
            search=search,
            role_id=role_id,
        )
    )


# =========================================================
# CAJEROS DE MI SUCURSAL
#
# ENCARGADO_SUCURSAL:
# - solo lectura
# - obtiene su sucursal desde EmployeeBranch
# - no acepta branch_id
# - devuelve únicamente cajeros activos
#
# IMPORTANTE:
# Debe estar antes de /{assignment_id}
# =========================================================

@router.get(
    "/my-branch",
    response_model=
        EmployeeBranchListResponse,
)
def get_my_branch_cashiers(
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
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_employee_branches_view
    ),
):

    try:

        return (
            EmployeeBranchService
            .get_my_branch_cashiers(
                db=db,
                current_user=current_user,
                page=page,
                page_size=page_size,
                search=search,
            )
        )

    except PermissionError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# PERSONAL DE UNA SUCURSAL
# =========================================================

@router.get(
    "/branch/{branch_id}",
    response_model=
        EmployeeBranchListResponse,
)
def get_staff_by_branch(
    branch_id: int,
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
    role_id: int | None = Query(
        default=None,
        gt=0,
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_employee_branches_manage
    ),
):

    try:

        return (
            EmployeeBranchService
            .get_branch_staff(
                db=db,
                branch_id=branch_id,
                page=page,
                page_size=page_size,
                search=search,
                role_id=role_id,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# HISTORIAL DE EMPLEADO
# =========================================================

@router.get(
    "/history/{user_id}",
    response_model=
        EmployeeBranchListResponse,
)
def get_employee_history(
    user_id: int,
    page: int = Query(
        default=1,
        ge=1,
    ),
    page_size: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_employee_branches_manage
    ),
):

    try:

        return (
            EmployeeBranchService
            .get_employee_history(
                db=db,
                user_id=user_id,
                page=page,
                page_size=page_size,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# ASIGNAR EMPLEADO
# =========================================================

@router.post(
    "",
    response_model=
        EmployeeBranchResponse,
    status_code=
        status.HTTP_201_CREATED,
)
def assign_employee(
    payload: EmployeeBranchCreate,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_employee_branches_manage
    ),
):

    try:

        return (
            EmployeeBranchService
            .assign_employee(
                db=db,
                payload=payload,
                performed_by_user_id=
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
# OBTENER ASIGNACIÓN
# =========================================================

@router.get(
    "/{assignment_id}",
    response_model=
        EmployeeBranchResponse,
)
def get_assignment(
    assignment_id: int,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_employee_branches_manage
    ),
):

    try:

        return (
            EmployeeBranchService
            .get_assignment(
                db=db,
                assignment_id=
                    assignment_id,
            )
        )

    except LookupError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc


# =========================================================
# REASIGNAR
# =========================================================

@router.patch(
    "/{assignment_id}/reassign",
    response_model=
        EmployeeBranchResponse,
)
def reassign_employee(
    assignment_id: int,
    payload:
        EmployeeBranchReassign,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_employee_branches_manage
    ),
):

    try:

        return (
            EmployeeBranchService
            .reassign_employee(
                db=db,
                assignment_id=
                    assignment_id,
                payload=payload,
                performed_by_user_id=
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
# QUITAR EMPLEADO
# =========================================================

@router.delete(
    "/{assignment_id}",
    response_model=
        EmployeeBranchResponse,
)
def remove_employee(
    assignment_id: int,
    request: Request,
    db: Session = Depends(
        get_db
    ),
    current_user: User = Depends(
        require_employee_branches_manage
    ),
):

    try:

        return (
            EmployeeBranchService
            .remove_employee(
                db=db,
                assignment_id=
                    assignment_id,
                performed_by_user_id=
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