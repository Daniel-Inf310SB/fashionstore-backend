import math
import re

from sqlalchemy import (
    func,
    or_,
    select,
)

from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.models.permission import Permission
from app.models.role import Role

from app.schemas.role import (
    RoleCreate,
    RoleUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class RoleService:

    # =====================================================
    # ROLES DEL SISTEMA
    # =====================================================

    SYSTEM_ROLES = {
        "ADMINISTRADOR",
        "ENCARGADO_SUCURSAL",
        "CAJERO",
        "CLIENTE",
        "PROVEEDOR",
    }


    # =====================================================
    # SNAPSHOT PARA BITÁCORA
    # =====================================================

    @staticmethod
    def role_snapshot(
        role: Role,
    ) -> dict:

        return {
            "id":
                role.id,

            "name":
                role.name,

            "description":
                role.description,

            "is_active":
                role.is_active,

            "permission_ids": [
                permission.id
                for permission
                in role.permissions
            ],
        }


    # =====================================================
    # NORMALIZAR NOMBRE
    # =====================================================

    @staticmethod
    def normalize_name(
        name: str,
    ) -> str:

        normalized = (
            name
            .strip()
            .upper()
        )

        normalized = re.sub(
            r"\s+",
            "_",
            normalized,
        )

        normalized = re.sub(
            r"[^A-Z0-9_]",
            "",
            normalized,
        )

        return normalized


    # =====================================================
    # LISTAR ROLES
    # =====================================================

    @staticmethod
    def list_roles(
        db: Session,

        page: int = 1,

        page_size: int = 20,

        search: str | None = None,

        is_active: bool | None = None,

        sort_by: str = "name",

        sort_order: str = "asc",
    ) -> dict:

        filters = []

        # =================================================
        # BÚSQUEDA
        # =================================================

        if search:

            search_value = (
                f"%{search.strip()}%"
            )

            filters.append(
                or_(
                    Role.name.ilike(
                        search_value
                    ),

                    Role.description.ilike(
                        search_value
                    ),
                )
            )

        # =================================================
        # ESTADO
        # =================================================

        if is_active is not None:

            filters.append(
                Role.is_active
                == is_active
            )

        # =================================================
        # TOTAL
        # =================================================

        count_statement = (
            select(
                func.count(
                    Role.id
                )
            )
            .where(
                *filters
            )
        )

        total = (
            db.scalar(
                count_statement
            )
            or 0
        )

        # =================================================
        # ORDENAMIENTO
        # =================================================

        sort_columns = {
            "id":
                Role.id,

            "name":
                Role.name,

            "created_at":
                Role.created_at,

            "updated_at":
                Role.updated_at,
        }

        sort_column = (
            sort_columns.get(
                sort_by,
                Role.name,
            )
        )

        if (
            sort_order.lower()
            == "desc"
        ):

            ordering = (
                sort_column.desc()
            )

        else:

            ordering = (
                sort_column.asc()
            )

        # =================================================
        # CONSULTA
        # =================================================

        statement = (
            select(
                Role
            )
            .options(
                selectinload(
                    Role.permissions
                )
            )
            .where(
                *filters
            )
            .order_by(
                ordering
            )
            .offset(
                (page - 1)
                * page_size
            )
            .limit(
                page_size
            )
        )

        roles = (
            db.scalars(
                statement
            )
            .all()
        )

        total_pages = (
            math.ceil(
                total
                / page_size
            )
            if total > 0
            else 0
        )

        return {
            "items":
                roles,

            "page":
                page,

            "page_size":
                page_size,

            "total":
                total,

            "total_pages":
                total_pages,
        }


    # =====================================================
    # OBTENER ROL
    # =====================================================

    @staticmethod
    def get_role(
        db: Session,

        role_id: int,
    ) -> Role:

        statement = (
            select(
                Role
            )
            .options(
                selectinload(
                    Role.permissions
                )
            )
            .where(
                Role.id
                == role_id
            )
        )

        role = db.scalar(
            statement
        )

        if role is None:

            raise ValueError(
                "Rol no encontrado"
            )

        return role


    # =====================================================
    # CREAR ROL
    # =====================================================

    @staticmethod
    def create_role(
        db: Session,

        data: RoleCreate,

        current_user_id:
            int | None = None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> Role:

        normalized_name = (
            RoleService.normalize_name(
                data.name
            )
        )

        if not normalized_name:

            raise ValueError(
                "El nombre del rol no es válido"
            )

        existing_role = db.scalar(
            select(
                Role
            ).where(
                Role.name
                == normalized_name
            )
        )

        if existing_role is not None:

            raise ValueError(
                "Ya existe un rol con ese nombre"
            )

        # =================================================
        # PERMISOS
        # =================================================

        permissions = []

        if data.permission_ids:

            unique_ids = list(
                set(
                    data.permission_ids
                )
            )

            permissions = (
                db.scalars(
                    select(
                        Permission
                    ).where(
                        Permission.id.in_(
                            unique_ids
                        ),

                        Permission.is_active
                        .is_(
                            True
                        ),
                    )
                )
                .all()
            )

            if (
                len(permissions)
                != len(unique_ids)
            ):

                raise ValueError(
                    "Uno o más permisos no existen "
                    "o están desactivados"
                )

        # =================================================
        # ROL
        # =================================================

        role = Role(
            name=
                normalized_name,

            description=(
                data.description.strip()
                if data.description
                and data.description.strip()
                else None
            ),

            is_active=
                True,
        )

        role.permissions = (
            permissions
        )

        db.add(
            role
        )

        try:

            db.flush()

            # =================================================
            # BITÁCORA
            # =================================================

            AuditLogService.log(
                db=db,

                user_id=
                    current_user_id,

                action=
                    "CREATE_ROLE",

                module=
                    "ROLES",

                entity_type=
                    "Role",

                entity_id=
                    role.id,

                description=(
                    f"Se creó el rol "
                    f"{role.name}"
                ),

                old_values=
                    None,

                new_values=
                    RoleService.role_snapshot(
                        role
                    ),

                ip_address=
                    ip_address,

                user_agent=
                    user_agent,

                status=
                    "SUCCESS",
            )

            db.commit()

        except Exception:

            db.rollback()

            raise

        db.refresh(
            role
        )

        return (
            RoleService.get_role(
                db=db,

                role_id=
                    role.id,
            )
        )


    # =====================================================
    # ACTUALIZAR ROL
    # =====================================================

    @staticmethod
    def update_role(
        db: Session,

        role_id: int,

        data: RoleUpdate,

        current_user_id:
            int | None = None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> Role:

        role = (
            RoleService.get_role(
                db=db,

                role_id=
                    role_id,
            )
        )

        old_values = (
            RoleService.role_snapshot(
                role
            )
        )

        # =================================================
        # NOMBRE
        # =================================================

        if data.name is not None:

            if (
                role.name
                in RoleService.SYSTEM_ROLES
            ):

                raise ValueError(
                    "Los roles base del sistema "
                    "no pueden cambiar de nombre"
                )

            normalized_name = (
                RoleService.normalize_name(
                    data.name
                )
            )

            if not normalized_name:

                raise ValueError(
                    "El nombre del rol no es válido"
                )

            existing_role = db.scalar(
                select(
                    Role
                ).where(
                    Role.name
                    == normalized_name,

                    Role.id
                    != role.id,
                )
            )

            if existing_role is not None:

                raise ValueError(
                    "Ya existe un rol con ese nombre"
                )

            role.name = (
                normalized_name
            )

        # =================================================
        # DESCRIPCIÓN
        # =================================================

        if data.description is not None:

            role.description = (
                data.description.strip()
                if data.description.strip()
                else None
            )

        # =================================================
        # ESTADO
        # =================================================

        if data.is_active is not None:

            if (
                not data.is_active
                and role.name
                in RoleService.SYSTEM_ROLES
            ):

                raise ValueError(
                    "Los roles base del sistema "
                    "no pueden desactivarse"
                )

            role.is_active = (
                data.is_active
            )

        # =================================================
        # SAVE + BITÁCORA
        # =================================================

        try:

            db.flush()

            AuditLogService.log(
                db=db,

                user_id=
                    current_user_id,

                action=
                    "UPDATE_ROLE",

                module=
                    "ROLES",

                entity_type=
                    "Role",

                entity_id=
                    role.id,

                description=(
                    f"Se actualizó el rol "
                    f"{role.name}"
                ),

                old_values=
                    old_values,

                new_values=
                    RoleService.role_snapshot(
                        role
                    ),

                ip_address=
                    ip_address,

                user_agent=
                    user_agent,

                status=
                    "SUCCESS",
            )

            db.commit()

        except Exception:

            db.rollback()

            raise

        db.refresh(
            role
        )

        return (
            RoleService.get_role(
                db=db,

                role_id=
                    role.id,
            )
        )


    # =====================================================
    # ASIGNAR PERMISOS
    # =====================================================

    @staticmethod
    def update_permissions(
        db: Session,

        role_id: int,

        permission_ids: list[int],

        current_user_id:
            int | None = None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> Role:

        role = (
            RoleService.get_role(
                db=db,

                role_id=
                    role_id,
            )
        )

        old_values = (
            RoleService.role_snapshot(
                role
            )
        )

        unique_ids = list(
            set(
                permission_ids
            )
        )

        # =================================================
        # SIN PERMISOS
        # =================================================

        if not unique_ids:

            role.permissions = []

            try:

                db.flush()

                AuditLogService.log(
                    db=db,

                    user_id=
                        current_user_id,

                    action=
                        "ASSIGN_ROLE_PERMISSIONS",

                    module=
                        "ROLES",

                    entity_type=
                        "Role",

                    entity_id=
                        role.id,

                    description=(
                        f"Se actualizaron los permisos "
                        f"del rol {role.name}"
                    ),

                    old_values=
                        old_values,

                    new_values=
                        RoleService.role_snapshot(
                            role
                        ),

                    ip_address=
                        ip_address,

                    user_agent=
                        user_agent,

                    status=
                        "SUCCESS",
                )

                db.commit()

            except Exception:

                db.rollback()

                raise

            return (
                RoleService.get_role(
                    db=db,

                    role_id=
                        role.id,
                )
            )

        # =================================================
        # BUSCAR PERMISOS
        # =================================================

        permissions = (
            db.scalars(
                select(
                    Permission
                ).where(
                    Permission.id.in_(
                        unique_ids
                    ),

                    Permission.is_active
                    .is_(
                        True
                    ),
                )
            )
            .all()
        )

        if (
            len(permissions)
            != len(unique_ids)
        ):

            raise ValueError(
                "Uno o más permisos no existen "
                "o están desactivados"
            )

        role.permissions = (
            permissions
        )

        try:

            db.flush()

            AuditLogService.log(
                db=db,

                user_id=
                    current_user_id,

                action=
                    "ASSIGN_ROLE_PERMISSIONS",

                module=
                    "ROLES",

                entity_type=
                    "Role",

                entity_id=
                    role.id,

                description=(
                    f"Se actualizaron los permisos "
                    f"del rol {role.name}"
                ),

                old_values=
                    old_values,

                new_values=
                    RoleService.role_snapshot(
                        role
                    ),

                ip_address=
                    ip_address,

                user_agent=
                    user_agent,

                status=
                    "SUCCESS",
            )

            db.commit()

        except Exception:

            db.rollback()

            raise

        return (
            RoleService.get_role(
                db=db,

                role_id=
                    role.id,
            )
        )


    # =====================================================
    # DESACTIVAR ROL
    # =====================================================

    @staticmethod
    def delete_role(
        db: Session,

        role_id: int,

        current_user_id:
            int | None = None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> None:

        role = (
            RoleService.get_role(
                db=db,

                role_id=
                    role_id,
            )
        )

        if (
            role.name
            in RoleService.SYSTEM_ROLES
        ):

            raise ValueError(
                "Los roles base del sistema "
                "no pueden eliminarse"
            )

        # =================================================
        # USUARIOS ASIGNADOS
        # =================================================

        if role.users:

            raise ValueError(
                "No puedes desactivar este rol "
                "porque tiene usuarios asignados"
            )

        old_values = (
            RoleService.role_snapshot(
                role
            )
        )

        role.is_active = False

        try:

            db.flush()

            AuditLogService.log(
                db=db,

                user_id=
                    current_user_id,

                action=
                    "DEACTIVATE_ROLE",

                module=
                    "ROLES",

                entity_type=
                    "Role",

                entity_id=
                    role.id,

                description=(
                    f"Se desactivó el rol "
                    f"{role.name}"
                ),

                old_values=
                    old_values,

                new_values=
                    RoleService.role_snapshot(
                        role
                    ),

                ip_address=
                    ip_address,

                user_agent=
                    user_agent,

                status=
                    "SUCCESS",
            )

            db.commit()

        except Exception:

            db.rollback()

            raise
