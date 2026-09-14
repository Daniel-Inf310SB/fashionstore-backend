import math

from sqlalchemy import asc, desc, func, select
from sqlalchemy.orm import Session

from app.models.city import City
from app.schemas.city import CityCreate, CityUpdate
from app.services.audit_log_service import AuditLogService


class CityService:

    # =====================================================
    # LISTAR CIUDADES
    # =====================================================

    @staticmethod
    def list_cities(
        db: Session,
        *,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        is_active: bool | None = None,
        sort_by: str = "name",
        sort_order: str = "asc",
    ) -> dict:

        page = max(page, 1)
        page_size = min(max(page_size, 1), 100)

        filters = []

        # -------------------------------------------------
        # BUSCADOR
        # -------------------------------------------------

        if search:
            search = search.strip()

            if search:
                filters.append(
                    City.name.ilike(f"%{search}%")
                )

        # -------------------------------------------------
        # ESTADO
        # -------------------------------------------------

        if is_active is not None:
            filters.append(
                City.is_active == is_active
            )

        # -------------------------------------------------
        # TOTAL
        # -------------------------------------------------

        count_stmt = (
            select(func.count(City.id))
            .where(*filters)
        )

        total = db.scalar(count_stmt) or 0

        # -------------------------------------------------
        # ORDENAMIENTO
        # -------------------------------------------------

        sort_columns = {
            "id": City.id,
            "name": City.name,
            "is_active": City.is_active,
        }

        sort_column = sort_columns.get(
            sort_by,
            City.name,
        )

        order_expression = (
            desc(sort_column)
            if sort_order.lower() == "desc"
            else asc(sort_column)
        )

        # -------------------------------------------------
        # CONSULTA
        # -------------------------------------------------

        stmt = (
            select(City)
            .where(*filters)
            .order_by(order_expression)
            .offset((page - 1) * page_size)
            .limit(page_size)
        )

        cities = db.scalars(stmt).all()

        total_pages = (
            math.ceil(total / page_size)
            if total > 0
            else 0
        )

        return {
            "items": list(cities),
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": total_pages,
        }

    # =====================================================
    # OBTENER CIUDAD
    # =====================================================

    @staticmethod
    def get_city(
        db: Session,
        city_id: int,
    ) -> City:

        city = db.get(
            City,
            city_id,
        )

        if not city:
            raise LookupError(
                "Ciudad no encontrada."
            )

        return city

    # =====================================================
    # CREAR CIUDAD
    # =====================================================

    @staticmethod
    def create_city(
        db: Session,
        data: CityCreate,
        *,
        current_user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> City:

        city_name = data.name.strip()

        # -------------------------------------------------
        # VALIDAR DUPLICADO
        # -------------------------------------------------

        existing = db.scalar(
            select(City)
            .where(
                func.lower(City.name)
                == city_name.lower()
            )
        )

        if existing:
            raise ValueError(
                "Ya existe una ciudad con ese nombre."
            )

        # -------------------------------------------------
        # CREAR
        # -------------------------------------------------

        city = City(
            name=city_name,
            is_active=True,
        )

        db.add(city)
        db.flush()

        # -------------------------------------------------
        # BITÁCORA
        # -------------------------------------------------

        AuditLogService.log(
            db=db,
            user_id=current_user_id,
            action="CREATE_CITY",
            module="BRANCHES",
            entity_type="City",
            entity_id=city.id,
            description=f"Se creó la ciudad {city.name}.",
            old_values=None,
            new_values={
                "id": city.id,
                "name": city.name,
                "is_active": city.is_active,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()
        db.refresh(city)

        return city

    # =====================================================
    # ACTUALIZAR CIUDAD
    # =====================================================

    @staticmethod
    def update_city(
        db: Session,
        city_id: int,
        data: CityUpdate,
        *,
        current_user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> City:

        city = CityService.get_city(
            db,
            city_id,
        )

        old_values = {
            "id": city.id,
            "name": city.name,
            "is_active": city.is_active,
        }

        update_data = data.model_dump(
            exclude_unset=True
        )

        # -------------------------------------------------
        # VALIDAR NOMBRE
        # -------------------------------------------------

        if "name" in update_data:

            city_name = (
                update_data["name"]
                .strip()
            )

            existing = db.scalar(
                select(City)
                .where(
                    func.lower(City.name)
                    == city_name.lower(),
                    City.id != city_id,
                )
            )

            if existing:
                raise ValueError(
                    "Ya existe otra ciudad con ese nombre."
                )

            city.name = city_name

        # -------------------------------------------------
        # ESTADO
        # -------------------------------------------------

        if "is_active" in update_data:
            city.is_active = update_data[
                "is_active"
            ]

        db.flush()

        new_values = {
            "id": city.id,
            "name": city.name,
            "is_active": city.is_active,
        }

        # -------------------------------------------------
        # BITÁCORA
        # -------------------------------------------------

        AuditLogService.log(
            db=db,
            user_id=current_user_id,
            action="UPDATE_CITY",
            module="BRANCHES",
            entity_type="City",
            entity_id=city.id,
            description=f"Se actualizó la ciudad {city.name}.",
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()
        db.refresh(city)

        return city

    # =====================================================
    # DESACTIVAR CIUDAD
    # =====================================================

    @staticmethod
    def deactivate_city(
        db: Session,
        city_id: int,
        *,
        current_user_id: int | None = None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> City:

        city = CityService.get_city(
            db,
            city_id,
        )

        if not city.is_active:
            raise ValueError(
                "La ciudad ya se encuentra desactivada."
            )

        old_values = {
            "id": city.id,
            "name": city.name,
            "is_active": city.is_active,
        }

        city.is_active = False

        db.flush()

        # -------------------------------------------------
        # BITÁCORA
        # -------------------------------------------------

        AuditLogService.log(
            db=db,
            user_id=current_user_id,
            action="DEACTIVATE_CITY",
            module="BRANCHES",
            entity_type="City",
            entity_id=city.id,
            description=f"Se desactivó la ciudad {city.name}.",
            old_values=old_values,
            new_values={
                "id": city.id,
                "name": city.name,
                "is_active": False,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()
        db.refresh(city)

        return city