import math

from datetime import date
from typing import Literal

from sqlalchemy import (
    func,
    or_,
)

from sqlalchemy.orm import Session

from app.models.collection import Collection

from app.schemas.collection import (
    CollectionCreate,
    CollectionUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


class CollectionService:

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_collections(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        is_active: bool | None = None,
        launch_date_from: date | None = None,
        launch_date_to: date | None = None,
        sort_by: Literal[
            "id",
            "name",
            "launch_date",
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
            Collection
        )

        # =================================================
        # BÚSQUEDA
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
                        Collection.name.ilike(
                            pattern
                        ),
                        Collection.description.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # ESTADO
        # =================================================

        if is_active is not None:

            query = query.filter(
                Collection.is_active
                == is_active
            )

        # =================================================
        # FECHA DESDE
        # =================================================

        if launch_date_from is not None:

            query = query.filter(
                Collection.launch_date
                >= launch_date_from
            )

        # =================================================
        # FECHA HASTA
        # =================================================

        if launch_date_to is not None:

            query = query.filter(
                Collection.launch_date
                <= launch_date_to
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
                Collection.id,

            "name":
                Collection.name,

            "launch_date":
                Collection.launch_date,

            "is_active":
                Collection.is_active,

            "created_at":
                Collection.created_at,

            "updated_at":
                Collection.updated_at,
        }

        sort_column = (
            sort_columns[
                sort_by
            ]
        )

        if sort_order == "desc":

            query = query.order_by(
                sort_column.desc(),
                Collection.id.desc(),
            )

        else:

            query = query.order_by(
                sort_column.asc(),
                Collection.id.asc(),
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
    # OBTENER
    # =====================================================

    @staticmethod
    def get_collection(
        db: Session,
        collection_id: int,
    ) -> Collection:

        collection = db.get(
            Collection,
            collection_id,
        )

        if collection is None:

            raise LookupError(
                "Colección no encontrada."
            )

        return collection

    # =====================================================
    # VALIDAR NOMBRE
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

        query = (
            db.query(
                Collection
            )
            .filter(
                func.lower(
                    Collection.name
                )
                ==
                clean_name.lower()
            )
        )

        if exclude_id is not None:

            query = query.filter(
                Collection.id
                != exclude_id
            )

        if query.first() is not None:

            raise ValueError(
                "Ya existe una colección "
                "con ese nombre."
            )

    # =====================================================
    # CREAR
    # =====================================================

    @staticmethod
    def create_collection(
        db: Session,
        payload: CollectionCreate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Collection:

        clean_name = (
            payload.name.strip()
        )

        clean_description = (
            payload.description.strip()
            if payload.description
            else None
        )

        CollectionService._validate_unique_name(
            db=db,
            name=clean_name,
        )

        collection = Collection(
            name=
                clean_name,

            description=
                clean_description,

            launch_date=
                payload.launch_date,

            is_active=
                True,
        )

        db.add(
            collection
        )

        db.flush()

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "CREATE_COLLECTION",

            module=
                "CATALOG",

            entity_type=
                "Collection",

            entity_id=
                collection.id,

            description=(
                f"Se creó la colección "
                f"'{collection.name}'."
            ),

            old_values=
                None,

            new_values={
                "name":
                    collection.name,

                "description":
                    collection.description,

                "launch_date": (
                    collection.launch_date.isoformat()
                    if collection.launch_date
                    else None
                ),

                "is_active":
                    collection.is_active,
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
            collection
        )

        return collection

    # =====================================================
    # ACTUALIZAR
    # =====================================================

    @staticmethod
    def update_collection(
        db: Session,
        collection_id: int,
        payload: CollectionUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Collection:

        collection = (
            CollectionService
            .get_collection(
                db=db,
                collection_id=
                    collection_id,
            )
        )

        old_values = {
            "name":
                collection.name,

            "description":
                collection.description,

            "launch_date": (
                collection.launch_date.isoformat()
                if collection.launch_date
                else None
            ),

            "is_active":
                collection.is_active,
        }

        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )

        if (
            "name" in update_data
            and update_data[
                "name"
            ] is not None
        ):

            clean_name = (
                update_data[
                    "name"
                ].strip()
            )

            CollectionService._validate_unique_name(
                db=db,
                name=clean_name,
                exclude_id=
                    collection.id,
            )

            collection.name = (
                clean_name
            )

        if (
            "description"
            in update_data
        ):

            description = (
                update_data[
                    "description"
                ]
            )

            collection.description = (
                description.strip()
                if description
                else None
            )

        if (
            "launch_date"
            in update_data
        ):

            collection.launch_date = (
                update_data[
                    "launch_date"
                ]
            )

        if (
            "is_active"
            in update_data
            and update_data[
                "is_active"
            ] is not None
        ):

            collection.is_active = (
                update_data[
                    "is_active"
                ]
            )

        db.flush()

        new_values = {
            "name":
                collection.name,

            "description":
                collection.description,

            "launch_date": (
                collection.launch_date.isoformat()
                if collection.launch_date
                else None
            ),

            "is_active":
                collection.is_active,
        }

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "UPDATE_COLLECTION",

            module=
                "CATALOG",

            entity_type=
                "Collection",

            entity_id=
                collection.id,

            description=(
                f"Se actualizó la colección "
                f"'{collection.name}'."
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
            collection
        )

        return collection

    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_collection(
        db: Session,
        collection_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Collection:

        collection = (
            CollectionService
            .get_collection(
                db=db,
                collection_id=
                    collection_id,
            )
        )

        if not collection.is_active:

            raise ValueError(
                "La colección ya se encuentra inactiva."
            )

        collection.is_active = (
            False
        )

        db.flush()

        AuditLogService.log(
            db=db,

            user_id=
                user_id,

            action=
                "DEACTIVATE_COLLECTION",

            module=
                "CATALOG",

            entity_type=
                "Collection",

            entity_id=
                collection.id,

            description=(
                f"Se desactivó la colección "
                f"'{collection.name}'."
            ),

            old_values={
                "is_active":
                    True,
            },

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
            collection
        )

        return collection