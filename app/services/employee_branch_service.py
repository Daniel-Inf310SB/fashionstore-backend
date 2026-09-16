import math

from datetime import (
    datetime,
    timezone,
)

from sqlalchemy import (
    or_,
    select,
)
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.branch import Branch
from app.models.employee_branch import (
    EmployeeBranch,
)
from app.models.role import Role
from app.models.user import User

from app.schemas.employee_branch import (
    EmployeeBranchCreate,
    EmployeeBranchReassign,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class EmployeeBranchService:

    # =====================================================
    # ROLES CONSIDERADOS PERSONAL DE SUCURSAL
    # =====================================================

    EMPLOYEE_ROLES = (
        "ENCARGADO_SUCURSAL",
        "CAJERO",
    )

    # =====================================================
    # QUERY BASE
    # =====================================================

    @staticmethod
    def _base_query(
        db: Session,
    ):

        return (
            db.query(
                EmployeeBranch
            )
            .options(
                joinedload(
                    EmployeeBranch.user
                ).joinedload(
                    User.role
                ),
                joinedload(
                    EmployeeBranch.branch
                ).joinedload(
                    Branch.city
                ),
            )
        )

    # =====================================================
    # OBTENER ASIGNACIÓN
    # =====================================================

    @staticmethod
    def get_assignment(
        db: Session,
        assignment_id: int,
    ) -> EmployeeBranch:

        assignment = (
            EmployeeBranchService
            ._base_query(db)
            .filter(
                EmployeeBranch.id
                == assignment_id
            )
            .first()
        )

        if assignment is None:
            raise LookupError(
                "Asignación de empleado no encontrada."
            )

        return assignment

    # =====================================================
    # LISTAR ASIGNACIONES
    # =====================================================

    @staticmethod
    def get_assignments(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        branch_id: int | None = None,
        role_id: int | None = None,
        is_active: bool | None = True,
    ) -> dict:

        page = max(
            page,
            1,
        )

        page_size = max(
            1,
            min(
                page_size,
                100,
            ),
        )

        query = (
            EmployeeBranchService
            ._base_query(db)
            .join(
                User,
                EmployeeBranch.user_id
                == User.id,
            )
            .join(
                Role,
                User.role_id
                == Role.id,
            )
            .join(
                Branch,
                EmployeeBranch.branch_id
                == Branch.id,
            )
            .filter(
                Role.name.in_(
                    EmployeeBranchService
                    .EMPLOYEE_ROLES
                )
            )
        )

        # =================================================
        # BUSCADOR
        # =================================================

        if search:

            clean_search = (
                search.strip()
            )

            if clean_search:

                pattern = (
                    f"%{clean_search}%"
                )

                query = query.filter(
                    or_(
                        User.first_name.ilike(
                            pattern
                        ),
                        User.last_name.ilike(
                            pattern
                        ),
                        User.email.ilike(
                            pattern
                        ),
                        User.username.ilike(
                            pattern
                        ),
                        User.document_number.ilike(
                            pattern
                        ),
                        Branch.name.ilike(
                            pattern
                        ),
                        Role.name.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # FILTRO SUCURSAL
        # =================================================

        if branch_id is not None:

            query = query.filter(
                EmployeeBranch.branch_id
                == branch_id
            )

        # =================================================
        # FILTRO ROL
        # =================================================

        if role_id is not None:

            query = query.filter(
                User.role_id
                == role_id
            )

        # =================================================
        # FILTRO ESTADO
        # =================================================

        if is_active is not None:

            query = query.filter(
                EmployeeBranch.is_active
                == is_active
            )

        # =================================================
        # TOTAL
        # =================================================

        total = query.count()

        # =================================================
        # PAGINACIÓN
        # =================================================

        items = (
            query
            .order_by(
                User.first_name.asc(),
                User.last_name.asc(),
                EmployeeBranch.id.asc(),
            )
            .offset(
                (page - 1)
                * page_size
            )
            .limit(
                page_size
            )
            .all()
        )

        total_pages = (
            math.ceil(
                total / page_size
            )
            if total > 0
            else 0
        )

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }

    # =====================================================
    # PERSONAL DE UNA SUCURSAL
    # =====================================================

    @staticmethod
    def get_branch_staff(
        db: Session,
        branch_id: int,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        role_id: int | None = None,
    ) -> dict:

        branch = db.get(
            Branch,
            branch_id,
        )

        if branch is None:
            raise LookupError(
                "Sucursal no encontrada."
            )

        return (
            EmployeeBranchService
            .get_assignments(
                db=db,
                page=page,
                page_size=page_size,
                search=search,
                branch_id=branch_id,
                role_id=role_id,
                is_active=True,
            )
        )

    # =====================================================
    # CAJEROS DE MI SUCURSAL
    #
    # Uso exclusivo del ENCARGADO_SUCURSAL.
    # La sucursal se obtiene desde su asignación activa.
    # No se recibe branch_id desde el frontend.
    # =====================================================

    @staticmethod
    def get_my_branch_cashiers(
        db: Session,
        current_user: User,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
    ) -> dict:

        # =================================================
        # VALIDAR ROL
        # =================================================

        if (
            current_user.role is None
            or current_user.role.name
            != "ENCARGADO_SUCURSAL"
        ):
            raise PermissionError(
                "Solo un encargado de sucursal puede "
                "consultar el personal de su sucursal."
            )

        # =================================================
        # OBTENER SUCURSAL ACTIVA DEL ENCARGADO
        # =================================================

        manager_assignment = (
            db.query(
                EmployeeBranch
            )
            .filter(
                EmployeeBranch.user_id
                == current_user.id,
                EmployeeBranch.is_active
                .is_(True),
            )
            .first()
        )

        if manager_assignment is None:
            raise LookupError(
                "El encargado no tiene una sucursal "
                "activa asignada."
            )

        branch = db.get(
            Branch,
            manager_assignment.branch_id,
        )

        if branch is None:
            raise LookupError(
                "La sucursal asignada no existe."
            )

        if not branch.is_active:
            raise LookupError(
                "La sucursal asignada está inactiva."
            )

        # =================================================
        # PAGINACIÓN
        # =================================================

        page = max(
            page,
            1,
        )

        page_size = max(
            1,
            min(
                page_size,
                100,
            ),
        )

        # =================================================
        # SOLO CAJEROS ACTIVOS DE ESA SUCURSAL
        # =================================================

        query = (
            EmployeeBranchService
            ._base_query(db)
            .join(
                User,
                EmployeeBranch.user_id
                == User.id,
            )
            .join(
                Role,
                User.role_id
                == Role.id,
            )
            .filter(
                EmployeeBranch.branch_id
                == branch.id,
                EmployeeBranch.is_active
                .is_(True),
                User.is_active
                .is_(True),
                Role.is_active
                .is_(True),
                Role.name
                == "CAJERO",
            )
        )

        # =================================================
        # BUSCADOR
        # =================================================

        if search:

            clean_search = (
                search.strip()
            )

            if clean_search:

                pattern = (
                    f"%{clean_search}%"
                )

                query = query.filter(
                    or_(
                        User.first_name.ilike(
                            pattern
                        ),
                        User.last_name.ilike(
                            pattern
                        ),
                        User.email.ilike(
                            pattern
                        ),
                        User.username.ilike(
                            pattern
                        ),
                        User.document_number.ilike(
                            pattern
                        ),
                        User.phone.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # TOTAL
        # =================================================

        total = query.count()

        # =================================================
        # RESULTADOS
        # =================================================

        items = (
            query
            .order_by(
                User.first_name.asc(),
                User.last_name.asc(),
                EmployeeBranch.id.asc(),
            )
            .offset(
                (page - 1)
                * page_size
            )
            .limit(
                page_size
            )
            .all()
        )

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (
                math.ceil(
                    total / page_size
                )
                if total > 0
                else 0
            ),
        }


    # =====================================================
    # HISTORIAL DE UN EMPLEADO
    # =====================================================

    @staticmethod
    def get_employee_history(
        db: Session,
        user_id: int,
        page: int = 1,
        page_size: int = 10,
    ) -> dict:

        user = db.get(
            User,
            user_id,
        )

        if user is None:
            raise LookupError(
                "Empleado no encontrado."
            )

        page = max(
            page,
            1,
        )

        page_size = max(
            1,
            min(
                page_size,
                100,
            ),
        )

        query = (
            EmployeeBranchService
            ._base_query(db)
            .filter(
                EmployeeBranch.user_id
                == user_id
            )
        )

        total = query.count()

        items = (
            query
            .order_by(
                EmployeeBranch
                .assigned_at
                .desc(),
                EmployeeBranch
                .id
                .desc(),
            )
            .offset(
                (page - 1)
                * page_size
            )
            .limit(
                page_size
            )
            .all()
        )

        total_pages = (
            math.ceil(
                total / page_size
            )
            if total > 0
            else 0
        )

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }

    # =====================================================
    # EMPLEADOS DISPONIBLES
    # =====================================================

    @staticmethod
    def get_available_employees(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        role_id: int | None = None,
    ) -> dict:

        page = max(
            page,
            1,
        )

        page_size = max(
            1,
            min(
                page_size,
                100,
            ),
        )

        # Usuarios que ya tienen
        # una sucursal activa.

        active_assignment_users = (
            select(
                EmployeeBranch.user_id
            )
            .where(
                EmployeeBranch.is_active
                .is_(True)
            )
        )

        query = (
            db.query(User)
            .options(
                joinedload(
                    User.role
                )
            )
            .join(
                Role,
                User.role_id
                == Role.id,
            )
            .filter(
                User.is_active.is_(True),
                Role.is_active.is_(True),
                Role.name.in_(
                    EmployeeBranchService
                    .EMPLOYEE_ROLES
                ),
                ~User.id.in_(
                    active_assignment_users
                ),
            )
        )

        # =================================================
        # BUSCADOR
        # =================================================

        if search:

            clean_search = (
                search.strip()
            )

            if clean_search:

                pattern = (
                    f"%{clean_search}%"
                )

                query = query.filter(
                    or_(
                        User.first_name.ilike(
                            pattern
                        ),
                        User.last_name.ilike(
                            pattern
                        ),
                        User.email.ilike(
                            pattern
                        ),
                        User.username.ilike(
                            pattern
                        ),
                        User.document_number.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # ROLE
        # =================================================

        if role_id is not None:

            query = query.filter(
                User.role_id
                == role_id
            )

        total = query.count()

        items = (
            query
            .order_by(
                User.first_name.asc(),
                User.last_name.asc(),
                User.id.asc(),
            )
            .offset(
                (page - 1)
                * page_size
            )
            .limit(
                page_size
            )
            .all()
        )

        total_pages = (
            math.ceil(
                total / page_size
            )
            if total > 0
            else 0
        )

        return {
            "items": items,
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }

    # =====================================================
    # VALIDAR EMPLEADO
    # =====================================================

    @staticmethod
    def _validate_employee(
        db: Session,
        user_id: int,
    ) -> User:

        user = (
            db.query(User)
            .options(
                joinedload(
                    User.role
                )
            )
            .filter(
                User.id
                == user_id
            )
            .first()
        )

        if user is None:
            raise ValueError(
                "El empleado seleccionado no existe."
            )

        if not user.is_active:
            raise ValueError(
                "El empleado se encuentra inactivo."
            )

        if user.role is None:
            raise ValueError(
                "El usuario no tiene un rol asignado."
            )

        if not user.role.is_active:
            raise ValueError(
                "El rol del empleado se encuentra inactivo."
            )

        if (
            user.role.name
            not in
            EmployeeBranchService
            .EMPLOYEE_ROLES
        ):
            raise ValueError(
                "El usuario seleccionado no corresponde "
                "al personal asignable a sucursales."
            )

        return user

    # =====================================================
    # VALIDAR SUCURSAL
    # =====================================================

    @staticmethod
    def _validate_branch(
        db: Session,
        branch_id: int,
    ) -> Branch:

        branch = db.get(
            Branch,
            branch_id,
        )

        if branch is None:
            raise ValueError(
                "La sucursal seleccionada no existe."
            )

        if not branch.is_active:
            raise ValueError(
                "La sucursal seleccionada está inactiva."
            )

        return branch

    # =====================================================
    # ASIGNAR EMPLEADO
    # =====================================================

    @staticmethod
    def assign_employee(
        db: Session,
        payload: EmployeeBranchCreate,
        performed_by_user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> EmployeeBranch:

        user = (
            EmployeeBranchService
            ._validate_employee(
                db,
                payload.user_id,
            )
        )

        branch = (
            EmployeeBranchService
            ._validate_branch(
                db,
                payload.branch_id,
            )
        )

        # =================================================
        # VALIDAR ASIGNACIÓN ACTIVA
        # =================================================

        current_assignment = (
            db.query(
                EmployeeBranch
            )
            .filter(
                EmployeeBranch.user_id
                == user.id,
                EmployeeBranch.is_active
                .is_(True),
            )
            .first()
        )

        if current_assignment is not None:

            if (
                current_assignment.branch_id
                == branch.id
            ):
                raise ValueError(
                    "El empleado ya está asignado "
                    "a esta sucursal."
                )

            raise ValueError(
                "El empleado ya tiene una sucursal activa. "
                "Utiliza la opción Reasignar."
            )

        # =================================================
        # CREAR ASIGNACIÓN
        # =================================================

        assignment = EmployeeBranch(
            user_id=user.id,
            branch_id=branch.id,
            is_active=True,
            ended_at=None,
        )

        db.add(
            assignment
        )

        try:

            db.flush()

            # =============================================
            # AUDITORÍA
            # =============================================

            AuditLogService.log(
                db=db,
                user_id=
                    performed_by_user_id,
                action=
                    "ASSIGN_EMPLOYEE_BRANCH",
                module=
                    "BRANCHES",
                entity_type=
                    "EmployeeBranch",
                entity_id=
                    assignment.id,
                description=(
                    f"Se asignó a "
                    f"{user.first_name} "
                    f"{user.last_name or ''} "
                    f"a la sucursal "
                    f"'{branch.name}'."
                ),
                old_values=None,
                new_values={
                    "user_id":
                        user.id,
                    "branch_id":
                        branch.id,
                    "role":
                        user.role.name,
                    "is_active":
                        True,
                },
                ip_address=
                    ip_address,
                user_agent=
                    user_agent,
                status=
                    "SUCCESS",
            )

            db.commit()

        except IntegrityError as exc:

            db.rollback()

            raise ValueError(
                "El empleado ya tiene una "
                "asignación activa."
            ) from exc

        return (
            EmployeeBranchService
            .get_assignment(
                db,
                assignment.id,
            )
        )

    # =====================================================
    # REASIGNAR EMPLEADO
    # =====================================================

    @staticmethod
    def reassign_employee(
        db: Session,
        assignment_id: int,
        payload: EmployeeBranchReassign,
        performed_by_user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> EmployeeBranch:

        current = (
            EmployeeBranchService
            .get_assignment(
                db,
                assignment_id,
            )
        )

        if not current.is_active:

            raise ValueError(
                "La asignación seleccionada "
                "ya se encuentra finalizada."
            )

        new_branch = (
            EmployeeBranchService
            ._validate_branch(
                db,
                payload.branch_id,
            )
        )

        if (
            current.branch_id
            == new_branch.id
        ):

            raise ValueError(
                "El empleado ya pertenece "
                "a esa sucursal."
            )

        user = current.user

        old_branch = current.branch

        now = datetime.now(
            timezone.utc
        )

        # =================================================
        # FINALIZAR ASIGNACIÓN ACTUAL
        # =================================================

        current.is_active = False

        current.ended_at = now

        db.flush()

        # =================================================
        # NUEVA ASIGNACIÓN
        # =================================================

        new_assignment = EmployeeBranch(
            user_id=current.user_id,
            branch_id=new_branch.id,
            is_active=True,
            ended_at=None,
        )

        db.add(
            new_assignment
        )

        try:

            db.flush()

            # =============================================
            # AUDITORÍA
            # =============================================

            AuditLogService.log(
                db=db,
                user_id=
                    performed_by_user_id,
                action=
                    "REASSIGN_EMPLOYEE_BRANCH",
                module=
                    "BRANCHES",
                entity_type=
                    "EmployeeBranch",
                entity_id=
                    new_assignment.id,
                description=(
                    f"Se reasignó a "
                    f"{user.first_name} "
                    f"{user.last_name or ''} "
                    f"de la sucursal "
                    f"'{old_branch.name}' "
                    f"a '{new_branch.name}'."
                ),
                old_values={
                    "assignment_id":
                        current.id,
                    "branch_id":
                        old_branch.id,
                    "branch_name":
                        old_branch.name,
                    "is_active":
                        True,
                },
                new_values={
                    "assignment_id":
                        new_assignment.id,
                    "branch_id":
                        new_branch.id,
                    "branch_name":
                        new_branch.name,
                    "is_active":
                        True,
                },
                ip_address=
                    ip_address,
                user_agent=
                    user_agent,
                status=
                    "SUCCESS",
            )

            db.commit()

        except IntegrityError as exc:

            db.rollback()

            raise ValueError(
                "No se pudo reasignar al empleado. "
                "Verifica sus asignaciones activas."
            ) from exc

        return (
            EmployeeBranchService
            .get_assignment(
                db,
                new_assignment.id,
            )
        )

    # =====================================================
    # QUITAR EMPLEADO DE SUCURSAL
    # =====================================================

    @staticmethod
    def remove_employee(
        db: Session,
        assignment_id: int,
        performed_by_user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> EmployeeBranch:

        assignment = (
            EmployeeBranchService
            .get_assignment(
                db,
                assignment_id,
            )
        )

        if not assignment.is_active:

            raise ValueError(
                "El empleado ya fue retirado "
                "de esta sucursal."
            )

        user = assignment.user

        branch = assignment.branch

        assignment.is_active = False

        assignment.ended_at = (
            datetime.now(
                timezone.utc
            )
        )

        db.flush()

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,
            user_id=
                performed_by_user_id,
            action=
                "REMOVE_EMPLOYEE_BRANCH",
            module=
                "BRANCHES",
            entity_type=
                "EmployeeBranch",
            entity_id=
                assignment.id,
            description=(
                f"Se retiró a "
                f"{user.first_name} "
                f"{user.last_name or ''} "
                f"de la sucursal "
                f"'{branch.name}'."
            ),
            old_values={
                "user_id":
                    user.id,
                "branch_id":
                    branch.id,
                "is_active":
                    True,
                "ended_at":
                    None,
            },
            new_values={
                "user_id":
                    user.id,
                "branch_id":
                    branch.id,
                "is_active":
                    False,
                "ended_at":
                    assignment
                    .ended_at
                    .isoformat(),
            },
            ip_address=
                ip_address,
            user_agent=
                user_agent,
            status=
                "SUCCESS",
        )

        db.commit()

        return (
            EmployeeBranchService
            .get_assignment(
                db,
                assignment.id,
            )
        )