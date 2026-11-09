import math
from datetime import datetime, timezone
from typing import Literal

from sqlalchemy import (
    func,
    or_,
)
from sqlalchemy.orm import (
    Session,
    joinedload,
)

from app.models.branch import Branch
from app.models.tenant import Tenant
from app.models.tenant_subscription import TenantSubscription
from app.models.subscription_plan import SubscriptionPlan
from app.services.subscription_coverage import subscription_valid_now
from app.models.city import City
from app.models.employee_branch import EmployeeBranch
from app.services.audit_log_service import AuditLogService
from app.schemas.branch import (
    BranchCreate,
    BranchUpdate,
)


class BranchService:

    # =====================================================
    # MI SUCURSAL ACTIVA
    #
    # Obtiene la sucursal asociada al empleado autenticado.
    # No depende del módulo de ventas ni del rol CAJERO.
    # =====================================================

    @staticmethod
    def get_my_branch(
        db: Session,
        user_id: int,
    ) -> Branch:

        assignment = (
            db.query(
                EmployeeBranch
            )
            .options(
                joinedload(
                    EmployeeBranch.branch
                )
                .joinedload(
                    Branch.city
                )
            )
            .filter(
                EmployeeBranch.user_id
                == user_id,

                EmployeeBranch.is_active.is_(
                    True
                ),
            )
            .first()
        )


        if assignment is None:
            raise LookupError(
                "El usuario no tiene una sucursal activa asignada."
            )


        branch = (
            assignment.branch
        )


        if branch is None:
            raise LookupError(
                "La sucursal asignada no existe."
            )


        if not branch.is_active:
            raise ValueError(
                "La sucursal asignada está inactiva."
            )


        return branch

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def get_branches(
        db: Session,
        page: int = 1,
        page_size: int = 10,
        search: str | None = None,
        city_id: int | None = None,
        is_active: bool | None = None,
        sort_by: Literal[
            "id",
            "name",
            "city_id",
            "is_active",
            "created_at",
            "updated_at",
        ] = "name",
        sort_order: Literal[
            "asc",
            "desc",
        ] = "asc",
        tenant_id: int | None = None,
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
            db.query(Branch)
            .options(
                joinedload(Branch.city)
            )
            .join(
                City,
                Branch.city_id == City.id,
            )
        )

        # Solo registros del tenant; sin contexto jamás listar globalmente.
        if tenant_id is None:
            raise ValueError("Se necesita un tenant activo para listar sucursales.")
        query = query.filter(Branch.tenant_id == tenant_id)

        # =================================================
        # SEARCH
        # =================================================

        if search:
            clean_search = search.strip()

            if clean_search:
                pattern = (
                    f"%{clean_search}%"
                )

                query = query.filter(
                    or_(
                        Branch.name.ilike(
                            pattern
                        ),
                        Branch.address.ilike(
                            pattern
                        ),
                        Branch.phone.ilike(
                            pattern
                        ),
                        City.name.ilike(
                            pattern
                        ),
                    )
                )

        # =================================================
        # CITY
        # =================================================

        if city_id is not None:
            query = query.filter(
                Branch.city_id == city_id
            )

        # =================================================
        # STATUS
        # =================================================

        if is_active is not None:
            query = query.filter(
                Branch.is_active == is_active
            )

        # =================================================
        # TOTAL
        # =================================================

        total = query.count()

        # =================================================
        # ORDER
        # =================================================

        sort_columns = {
            "id": Branch.id,
            "name": Branch.name,
            "city_id": Branch.city_id,
            "is_active": Branch.is_active,
            "created_at": Branch.created_at,
            "updated_at": Branch.updated_at,
        }

        sort_column = sort_columns[
            sort_by
        ]

        if sort_order == "desc":
            query = query.order_by(
                sort_column.desc(),
                Branch.id.desc(),
            )

        else:
            query = query.order_by(
                sort_column.asc(),
                Branch.id.asc(),
            )

        # =================================================
        # PAGINATION
        # =================================================

        offset = (
            page - 1
        ) * page_size

        items = (
            query
            .offset(offset)
            .limit(page_size)
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
    # OBTENER POR ID
    # =====================================================

    @staticmethod
    def get_branch(
        db: Session,
        branch_id: int,
    ) -> Branch:

        branch = (
            db.query(Branch)
            .options(
                joinedload(Branch.city)
            )
            .filter(
                Branch.id == branch_id
            )
            .first()
        )

        if branch is None:
            raise LookupError(
                "Sucursal no encontrada."
            )

        return branch

    # =====================================================
    # VALIDAR CIUDAD
    # =====================================================

    @staticmethod
    def _get_valid_city(
        db: Session,
        city_id: int,
    ) -> City:

        city = db.get(
            City,
            city_id,
        )

        if city is None:
            raise ValueError(
                "La ciudad seleccionada no existe."
            )

        if not city.is_active:
            raise ValueError(
                "La ciudad seleccionada está inactiva."
            )

        return city

    # =====================================================
    # CREATE
    # =====================================================

    @staticmethod
    def create_branch(
        db: Session,
        payload: BranchCreate,
        user_id: int | None,
        tenant_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Branch:

        if tenant_id is None:
            raise ValueError("Se requiere una empresa autenticada para crear sucursales.")

        # Serializa altas concurrentes del mismo tenant para respetar el límite.
        tenant = (db.query(Tenant)
                  .filter(Tenant.id == tenant_id)
                  .with_for_update()
                  .one_or_none())
        if tenant is None or not tenant.is_active:
            raise ValueError("La empresa no está activa.")

        subscription = (db.query(TenantSubscription)
                        .filter(TenantSubscription.tenant_id == tenant_id)
                        .one_or_none())
        now = datetime.now(timezone.utc)
        if subscription is None or subscription.status != "ACTIVE":
            raise ValueError("La empresa necesita una suscripción activa.")
        if not subscription_valid_now(db, subscription, now):
            raise ValueError("La suscripción no cubre la fecha actual con un período pagado vigente.")

        plan = db.query(SubscriptionPlan).filter(SubscriptionPlan.id == subscription.plan_id).one_or_none()
        if plan is None or not plan.is_active:
            raise ValueError("El plan contratado no está disponible.")
        if plan.max_branches is not None:
            branch_count = (db.query(Branch)
                            .filter(Branch.tenant_id == tenant_id, Branch.is_active.is_(True))
                            .count())
            if branch_count >= plan.max_branches:
                raise ValueError(f"Tu plan permite como máximo {plan.max_branches} sucursal(es) activa(s).")

        # =================================================
        # VALIDAR CIUDAD
        # =================================================

        BranchService._get_valid_city(
            db,
            payload.city_id,
        )

        # =================================================
        # CREAR
        # =================================================

        branch = Branch(
            name=payload.name.strip(),
            address=payload.address.strip(),
            phone=(
                payload.phone.strip()
                if payload.phone
                else None
            ),
            latitude=payload.latitude,
            longitude=payload.longitude,
            city_id=payload.city_id,
            tenant_id=tenant_id,
            is_active=True,
        )

        db.add(branch)

        db.flush()

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="CREATE_BRANCH",
            module="BRANCHES",
            entity_type="Branch",
            entity_id=branch.id,
            description=(
                f"Se creó la sucursal "
                f"'{branch.name}'."
            ),
            old_values=None,
            new_values={
                "name": branch.name,
                "address": branch.address,
                "phone": branch.phone,
                "latitude": (
                    str(branch.latitude)
                    if branch.latitude is not None
                    else None
                ),
                "longitude": (
                    str(branch.longitude)
                    if branch.longitude is not None
                    else None
                ),
                "city_id": branch.city_id,
                "is_active": branch.is_active,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        db.refresh(branch)

        return BranchService.get_branch(
            db,
            branch.id,
        )

    # =====================================================
    # UPDATE
    # =====================================================

    @staticmethod
    def update_branch(
        db: Session,
        branch_id: int,
        payload: BranchUpdate,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Branch:

        branch = BranchService.get_branch(
            db,
            branch_id,
        )

        old_values = {
            "name": branch.name,
            "address": branch.address,
            "phone": branch.phone,
            "latitude": (
                str(branch.latitude)
                if branch.latitude is not None
                else None
            ),
            "longitude": (
                str(branch.longitude)
                if branch.longitude is not None
                else None
            ),
            "city_id": branch.city_id,
            "is_active": branch.is_active,
        }

        update_data = (
            payload.model_dump(
                exclude_unset=True
            )
        )

        # =================================================
        # VALIDAR CAMBIO DE CIUDAD
        # =================================================

        if (
            "city_id" in update_data
            and update_data["city_id"]
            is not None
        ):
            BranchService._get_valid_city(
                db,
                update_data["city_id"],
            )

        # =================================================
        # ACTUALIZAR NOMBRE
        # =================================================

        if "name" in update_data:
            branch.name = (
                update_data["name"].strip()
            )

        # =================================================
        # ACTUALIZAR DIRECCIÓN
        # =================================================

        if "address" in update_data:
            branch.address = (
                update_data[
                    "address"
                ].strip()
            )

        # =================================================
        # ACTUALIZAR TELÉFONO
        # =================================================

        if "phone" in update_data:
            phone = update_data["phone"]

            branch.phone = (
                phone.strip()
                if phone
                else None
            )

        # =================================================
        # LATITUDE
        # =================================================

        if "latitude" in update_data:
            branch.latitude = (
                update_data["latitude"]
            )

        # =================================================
        # LONGITUDE
        # =================================================

        if "longitude" in update_data:
            branch.longitude = (
                update_data["longitude"]
            )

        # =================================================
        # CITY
        # =================================================

        if (
            "city_id" in update_data
            and update_data["city_id"]
            is not None
        ):
            branch.city_id = (
                update_data["city_id"]
            )

        # =================================================
        # STATUS
        # =================================================

        if (
            "is_active" in update_data
            and update_data["is_active"]
            is not None
        ):
            # CU56: reactivar consume un cupo igual que crear una sucursal.
            # Bloqueamos la fila del tenant para serializar las altas/reactivaciones.
            if update_data["is_active"] and not branch.is_active:
                tenant = (db.query(Tenant)
                          .filter(Tenant.id == branch.tenant_id)
                          .with_for_update().one_or_none())
                if tenant is None or not tenant.is_active:
                    raise ValueError("La empresa no está activa.")
                subscription = (db.query(TenantSubscription)
                                .filter(TenantSubscription.tenant_id == branch.tenant_id)
                                .one_or_none())
                if subscription is None or not subscription_valid_now(db, subscription, datetime.now(timezone.utc)):
                    raise ValueError("Necesitas una suscripción vigente para reactivar sucursales.")
                plan = db.get(SubscriptionPlan, subscription.plan_id)
                if plan is None or not plan.is_active:
                    raise ValueError("El plan contratado no está disponible.")
                if plan.max_branches is not None:
                    active_count = (db.query(Branch)
                                    .filter(Branch.tenant_id == branch.tenant_id,
                                            Branch.is_active.is_(True)).count())
                    if active_count >= plan.max_branches:
                        raise ValueError(
                            f"Tu plan permite como máximo {plan.max_branches} sucursal(es) activa(s)."
                        )
            branch.is_active = update_data["is_active"]

        db.flush()

        new_values = {
            "name": branch.name,
            "address": branch.address,
            "phone": branch.phone,
            "latitude": (
                str(branch.latitude)
                if branch.latitude is not None
                else None
            ),
            "longitude": (
                str(branch.longitude)
                if branch.longitude is not None
                else None
            ),
            "city_id": branch.city_id,
            "is_active": branch.is_active,
        }

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="UPDATE_BRANCH",
            module="BRANCHES",
            entity_type="Branch",
            entity_id=branch.id,
            description=(
                f"Se actualizó la sucursal "
                f"'{branch.name}'."
            ),
            old_values=old_values,
            new_values=new_values,
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        return BranchService.get_branch(
            db,
            branch.id,
        )

    # =====================================================
    # DESACTIVAR
    # =====================================================

    @staticmethod
    def deactivate_branch(
        db: Session,
        branch_id: int,
        user_id: int | None,
        ip_address: str | None = None,
        user_agent: str | None = None,
    ) -> Branch:

        branch = BranchService.get_branch(
            db,
            branch_id,
        )

        if not branch.is_active:
            raise ValueError(
                "La sucursal ya se encuentra inactiva."
            )

        old_values = {
            "is_active": True,
        }

        branch.is_active = False

        db.flush()

        # =================================================
        # AUDITORÍA
        # =================================================

        AuditLogService.log(
            db=db,
            user_id=user_id,
            action="DEACTIVATE_BRANCH",
            module="BRANCHES",
            entity_type="Branch",
            entity_id=branch.id,
            description=(
                f"Se desactivó la sucursal "
                f"'{branch.name}'."
            ),
            old_values=old_values,
            new_values={
                "is_active": False,
            },
            ip_address=ip_address,
            user_agent=user_agent,
            status="SUCCESS",
        )

        db.commit()

        return BranchService.get_branch(
            db,
            branch.id,
        )