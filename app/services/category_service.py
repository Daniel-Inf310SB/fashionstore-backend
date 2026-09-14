import math

from typing import Literal

from sqlalchemy import (
    func,
    or_,
)
from sqlalchemy.orm import Session

from app.models.category import Category

from app.schemas.category import (
    CategoryCreate,
    CategoryUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class CategoryService:

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_categories(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        is_active: bool | None = None,
        sort_by: Literal[
            "id",
            "name",
            "is_active",
            "created_at",
            "updated_at",
        ] = "name",
        sort_order: Literal[
            "asc",
            "desc",
        ] = "asc",
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

        query = db.query(
            Category
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
                        Category.name.ilike(
                            pattern
                        ),
                        Category.description.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # ESTADO
        # =================================================

        if is_active is not None:

            query = query.filter(
                Category.is_active
                == is_active
            )

        # =================================================
        # TOTAL
        # =================================================

        total = query.count()

        # =================================================
        # ORDENAMIENTO
        # =================================================

        sort_columns = {
            "id":
                Category.id,

            "name":
                Category.name,

            "is_active":
                Category.is_active,

            "created_at":
                Category.created_at,

            "updated_at":
                Category.updated_at,
        }

        sort_column = (
            sort_columns[
                sort_by
            ]
        )

        if sort_order == "desc":

            query = query.order_by(
                sort_column.desc(),
                Category.id.desc(),
            )

        else:

            query = query.order_by(
                sort_column.asc(),
                Category.id.asc(),
            )

        # =================================================
        # PAGINACIÓN
        # =================================================

        items = (
            query
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
            "items":
                items,

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
    # OBTENER POR ID
    # =====================================================

    @staticmethod
    def get_category(
        db: Session,
        category_id: int,
    ) -> Category:

        category = db.get(
            Category,
            category_id,
        )

        if category is None:

            raise LookupError(
                "Categoría no encontrada."
            )

        return category

    # =====================================================
    # VALIDAR NOMBRE DUPLICADO
    # =====================================================

    @staticmethod
    def _validate_unique_name(
        db: Session,
        name: str,
        exclude_id: int | None = None,
    ) -> None:

        clean_name = (
            name.strip()
        )

        query = db.query(
            Category
        ).filter(
            func.lower(
                Category.name
            )
            ==
            clean_name.lower()
        )

        if exclude_id is not None:

            query = query.filter(
                Category.id
                != exclude_id
            )

        existing = (
            query.first()
        )

        if existing is not None:

            raise ValueError(
                "Ya existe una categoría "
                "con ese nombre."
            )

    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_category(
        db: Session,
        payload: CategoryCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Category:

        clean_name = (
            payload.name.strip()
        )

        clean_description = (
            payload.description.strip()
            if payload.description
            else None
        )

        CategoryService._validate_unique_name(
            db=db,
            name=clean_name,
        )

        category = Category(
            name=clean_name,

            description=
                clean_description,

            is_active=True,
        )

        db.add(
            category
        )

        db.flush()

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "CREATE_CATEGORY",

            module=
                "CATALOG",

            entity_type=
                "Category",

            entity_id=
                category.id,

            description=(
                f"Se creó la categoría "
                f"'{category.name}'."
            ),

            old_values=None,

            new_values={
                "name":
                    category.name,

                "description":
                    category.description,

                "is_active":
                    category.is_active,
            },

            ip_address=
                ip_address,

            user_agent=
                user_agent,

            status=
                "SUCCESS",
        )

        db.commit()

        db.refresh(
            category
        )

        return category

    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_category(
        db: Session,
        category_id: int,
        payload: CategoryUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Category:

        category = (
            CategoryService
            .get_category(
                db=db,
                category_id=
                    category_id,
            )
        )

        old_values = {
            "name":
                category.name,

            "description":
                category.description,

            "is_active":
                category.is_active,
        }

        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )

        # =================================================
        # NOMBRE
        # =================================================

        if (
            "name" in update_data
            and update_data["name"]
            is not None
        ):

            clean_name = (
                update_data[
                    "name"
                ].strip()
            )

            CategoryService._validate_unique_name(
                db=db,
                name=clean_name,
                exclude_id=
                    category.id,
            )

            category.name = (
                clean_name
            )

        # =================================================
        # DESCRIPCIÓN
        # =================================================

        if "description" in update_data:

            description = (
                update_data[
                    "description"
                ]
            )

            category.description = (
                description.strip()
                if description
                else None
            )

        # =================================================
        # ESTADO
        # =================================================

        if (
            "is_active" in update_data
            and update_data[
                "is_active"
            ]
            is not None
        ):

            category.is_active = (
                update_data[
                    "is_active"
                ]
            )

        db.flush()

        new_values = {
            "name":
                category.name,

            "description":
                category.description,

            "is_active":
                category.is_active,
        }

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_CATEGORY",

            module=
                "CATALOG",

            entity_type=
                "Category",

            entity_id=
                category.id,

            description=(
                f"Se actualizó la categoría "
                f"'{category.name}'."
            ),

            old_values=
                old_values,

            new_values=
                new_values,

            ip_address=
                ip_address,

            user_agent=
                user_agent,

            status=
                "SUCCESS",
        )

        db.commit()

        db.refresh(
            category
        )

        return category

    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_category(
        db: Session,
        category_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Category:

        category = (
            CategoryService
            .get_category(
                db=db,
                category_id=
                    category_id,
            )
        )

        if not category.is_active:

            raise ValueError(
                "La categoría ya se encuentra inactiva."
            )

        old_values = {
            "is_active":
                True,
        }

        category.is_active = (
            False
        )

        db.flush()

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "DEACTIVATE_CATEGORY",

            module=
                "CATALOG",

            entity_type=
                "Category",

            entity_id=
                category.id,

            description=(
                f"Se desactivó la categoría "
                f"'{category.name}'."
            ),

            old_values=
                old_values,

            new_values={
                "is_active":
                    False,
            },

            ip_address=
                ip_address,

            user_agent=
                user_agent,

            status=
                "SUCCESS",
        )

        db.commit()

        db.refresh(
            category
        )

        return category