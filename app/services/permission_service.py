import math

from sqlalchemy import (
    func,
    or_,
    select,
)

from sqlalchemy.orm import Session

from app.models.permission import Permission

from app.schemas.permission import (
    PermissionCreate,
    PermissionUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class PermissionService:

    # =====================================================
    # SNAPSHOT PARA BITÁCORA
    # =====================================================

    @staticmethod
    def permission_snapshot(
        permission: Permission,
    ) -> dict:

        return {
            "id":
                permission.id,

            "code":
                permission.code,

            "name":
                permission.name,

            "description":
                permission.description,

            "is_active":
                permission.is_active,
        }


    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def list_permissions(
        db: Session,

        page: int = 1,

        page_size: int = 20,

        search: str | None = None,

        is_active: bool | None = None,

        sort_by: str = "code",

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
                    Permission.code.ilike(
                        search_value
                    ),

                    Permission.name.ilike(
                        search_value
                    ),

                    Permission.description.ilike(
                        search_value
                    ),
                )
            )

        # =================================================
        # ESTADO
        # =================================================

        if is_active is not None:

            filters.append(
                Permission.is_active
                == is_active
            )

        # =================================================
        # TOTAL
        # =================================================

        total = (
            db.scalar(
                select(
                    func.count(
                        Permission.id
                    )
                )
                .where(
                    *filters
                )
            )
            or 0
        )

        # =================================================
        # ORDEN
        # =================================================

        sort_columns = {
            "id":
                Permission.id,

            "code":
                Permission.code,

            "name":
                Permission.name,

            "created_at":
                Permission.created_at,

            "updated_at":
                Permission.updated_at,
        }

        sort_column = (
            sort_columns.get(
                sort_by,
                Permission.code,
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
                Permission
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

        permissions = (
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
                permissions,

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
    # OBTENER
    # =====================================================

    @staticmethod
    def get_permission(
        db: Session,

        permission_id: int,
    ) -> Permission:

        permission = db.scalar(
            select(
                Permission
            ).where(
                Permission.id
                == permission_id
            )
        )

        if permission is None:

            raise ValueError(
                "Permiso no encontrado"
            )

        return permission


    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_permission(
        db: Session,

        data: PermissionCreate,

        current_user_id:
            int | None = None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> Permission:

        normalized_code = (
            data.code
            .strip()
            .lower()
        )

        if not normalized_code:

            raise ValueError(
                "El código del permiso no es válido"
            )

        existing = db.scalar(
            select(
                Permission
            ).where(
                Permission.code
                == normalized_code
            )
        )

        if existing is not None:

            raise ValueError(
                "Ya existe un permiso "
                "con ese código"
            )

        permission = Permission(
            code=
                normalized_code,

            name=
                data.name.strip(),

            description=(
                data.description.strip()
                if data.description
                and data.description.strip()
                else None
            ),

            is_active=
                True,
        )

        db.add(
            permission
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
                    "CREATE_PERMISSION",

                module=
                    "PERMISSIONS",

                entity_type=
                    "Permission",

                entity_id=
                    permission.id,

                description=(
                    f"Se creó el permiso "
                    f"{permission.code}"
                ),

                old_values=
                    None,

                new_values=
                    PermissionService
                    .permission_snapshot(
                        permission
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
            permission
        )

        return permission


    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_permission(
        db: Session,

        permission_id: int,

        data: PermissionUpdate,

        current_user_id:
            int | None = None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> Permission:

        permission = (
            PermissionService
            .get_permission(
                db=db,

                permission_id=
                    permission_id,
            )
        )

        old_values = (
            PermissionService
            .permission_snapshot(
                permission
            )
        )

        # =================================================
        # CODE
        # =================================================

        if data.code is not None:

            normalized_code = (
                data.code
                .strip()
                .lower()
            )

            if not normalized_code:

                raise ValueError(
                    "El código del permiso "
                    "no es válido"
                )

            existing = db.scalar(
                select(
                    Permission
                ).where(
                    Permission.code
                    == normalized_code,

                    Permission.id
                    != permission.id,
                )
            )

            if existing is not None:

                raise ValueError(
                    "Ya existe un permiso "
                    "con ese código"
                )

            permission.code = (
                normalized_code
            )

        # =================================================
        # NOMBRE
        # =================================================

        if data.name is not None:

            name = (
                data.name.strip()
            )

            if not name:

                raise ValueError(
                    "El nombre del permiso "
                    "es obligatorio"
                )

            permission.name = (
                name
            )

        # =================================================
        # DESCRIPCIÓN
        # =================================================

        if data.description is not None:

            permission.description = (
                data.description.strip()
                if data.description.strip()
                else None
            )

        # =================================================
        # ESTADO
        # =================================================

        if data.is_active is not None:

            permission.is_active = (
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
                    "UPDATE_PERMISSION",

                module=
                    "PERMISSIONS",

                entity_type=
                    "Permission",

                entity_id=
                    permission.id,

                description=(
                    f"Se actualizó el permiso "
                    f"{permission.code}"
                ),

                old_values=
                    old_values,

                new_values=
                    PermissionService
                    .permission_snapshot(
                        permission
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
            permission
        )

        return permission


    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def delete_permission(
        db: Session,

        permission_id: int,

        current_user_id:
            int | None = None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> None:

        permission = (
            PermissionService
            .get_permission(
                db=db,

                permission_id=
                    permission_id,
            )
        )

        if not permission.is_active:

            raise ValueError(
                "El permiso ya está desactivado"
            )

        old_values = (
            PermissionService
            .permission_snapshot(
                permission
            )
        )

        permission.is_active = False

        try:

            db.flush()

            AuditLogService.log(
                db=db,

                user_id=
                    current_user_id,

                action=
                    "DEACTIVATE_PERMISSION",

                module=
                    "PERMISSIONS",

                entity_type=
                    "Permission",

                entity_id=
                    permission.id,

                description=(
                    f"Se desactivó el permiso "
                    f"{permission.code}"
                ),

                old_values=
                    old_values,

                new_values=
                    PermissionService
                    .permission_snapshot(
                        permission
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
