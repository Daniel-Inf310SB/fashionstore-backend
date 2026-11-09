from app.services.subscription_coverage import subscription_valid_now
import math

from datetime import date, datetime, timezone

from sqlalchemy import (
    func,
    or_,
    select,
)

from sqlalchemy.orm import (
    Session,
    selectinload,
)

from app.core.security import (
    hash_password,
)

from app.models.role import Role
from app.models.tenant import Tenant
from app.models.subscription_plan import SubscriptionPlan
from app.models.tenant_subscription import TenantSubscription
from app.models.user import User

from app.schemas.user import (
    UserCreate,
    UserUpdate,
)

from app.services.audit_log_service import (
    AuditLogService,
)


# Mismos perfiles internos considerados por las restricciones de los planes SaaS.
INTERNAL_STAFF_ROLES = ("TENANT_ADMIN", "ENCARGADO_SUCURSAL", "CAJERO", "ADMINISTRADOR")


def enforce_staff_capacity(db: Session, tenant_id: int, *, added_staff: bool, exclude_user_id: int | None = None) -> None:
    """Serializa las altas por empresa y evita superar el cupo contratado.

    Solo se llama cuando una operación incrementa los usuarios internos activos.
    La cantidad de asignaciones a sucursales no consume cupos extra.
    """
    if not added_staff:
        return
    # El bloqueo debe mantenerse en la transacción que crea/reactiva al usuario.
    tenant = db.scalar(select(Tenant).where(Tenant.id == tenant_id).with_for_update())
    if tenant is None or not tenant.is_active:
        raise ValueError("La empresa no está disponible")
    sub = db.scalar(select(TenantSubscription).where(TenantSubscription.tenant_id == tenant_id))
    plan = db.get(SubscriptionPlan, sub.plan_id) if sub is not None else None
    if sub is None or plan is None or not plan.is_active:
        raise ValueError("La empresa no tiene un plan SaaS disponible")
    if not subscription_valid_now(db, sub, datetime.now(timezone.utc)):
        raise ValueError("Necesitas una suscripción vigente para incorporar o reactivar personal.")
    if plan.max_staff is None:
        return
    count_query = select(func.count(User.id)).join(Role, User.role_id == Role.id).where(
        User.tenant_id == tenant_id,
        User.is_active.is_(True),
        Role.name.in_(INTERNAL_STAFF_ROLES),
    )
    if exclude_user_id is not None:
        count_query = count_query.where(User.id != exclude_user_id)
    # Evita contar mutaciones del propio objeto pendientes de confirmar.
    with db.no_autoflush:
        current = db.scalar(count_query) or 0
    if current >= plan.max_staff:
        raise ValueError(
            f"Tu plan {plan.name} permite un máximo de {plan.max_staff} "
            "usuarios internos activos (incluidos administradores). "
            f"Actualmente tienes {current}. Cambia de plan o desactiva una cuenta."
        )


class UserService:

    # =====================================================
    # SERIALIZAR VALORES PARA BITÁCORA
    # =====================================================

    @staticmethod
    def user_snapshot(
        user: User,
    ) -> dict:

        def serialize(
            value,
        ):

            if isinstance(
                value,
                (
                    datetime,
                    date,
                ),
            ):

                return value.isoformat()

            return value

        return {
            "id":
                user.id,

            "username":
                user.username,

            "first_name":
                user.first_name,

            "last_name":
                user.last_name,

            "email":
                user.email,

            "phone":
                user.phone,

            "document_number":
                user.document_number,

            "address":
                user.address,

            "date_of_birth":
                serialize(
                    user.date_of_birth
                ),

            "role_id":
                user.role_id,

            "is_active":
                user.is_active,

            "is_verified":
                user.is_verified,

            "profile_completed":
                user.profile_completed,
        }

    # =====================================================
    # LISTAR
    # =====================================================

    @staticmethod
    def list_users(
        db: Session,

        page: int = 1,

        page_size: int = 10,

        search: str | None = None,

        role_id: int | None = None,

        is_active: bool | None = None,

        is_verified: bool | None = None,

        profile_completed: bool | None = None,

        sort_by: str = "created_at",

        sort_order: str = "desc",
        tenant_id: int | None = None,
    ) -> dict:

        filters = []
        if tenant_id is not None:
            filters.append(User.tenant_id == tenant_id)

        # =================================================
        # SEARCH
        # =================================================

        if (
            search
            and search.strip()
        ):

            value = (
                f"%{search.strip()}%"
            )

            filters.append(
                or_(
                    User.username.ilike(
                        value
                    ),

                    User.first_name.ilike(
                        value
                    ),

                    User.last_name.ilike(
                        value
                    ),

                    User.email.ilike(
                        value
                    ),

                    User.phone.ilike(
                        value
                    ),

                    User.document_number.ilike(
                        value
                    ),
                )
            )

        # =================================================
        # ROLE
        # =================================================

        if role_id is not None:

            filters.append(
                User.role_id
                == role_id
            )

        # =================================================
        # ACTIVE
        # =================================================

        if is_active is not None:

            filters.append(
                User.is_active
                == is_active
            )

        # =================================================
        # VERIFIED
        # =================================================

        if is_verified is not None:

            filters.append(
                User.is_verified
                == is_verified
            )

        # =================================================
        # PROFILE
        # =================================================

        if profile_completed is not None:

            filters.append(
                User.profile_completed
                == profile_completed
            )

        # =================================================
        # TOTAL
        # =================================================

        total = (
            db.scalar(
                select(
                    func.count(
                        User.id
                    )
                )
                .where(
                    *filters
                )
            )
            or 0
        )

        # =================================================
        # SORT
        # =================================================

        sort_columns = {
            "id":
                User.id,

            "username":
                User.username,

            "first_name":
                User.first_name,

            "email":
                User.email,

            "created_at":
                User.created_at,

            "updated_at":
                User.updated_at,

            "last_login_at":
                User.last_login_at,
        }

        sort_column = (
            sort_columns.get(
                sort_by,
                User.created_at,
            )
        )

        if (
            sort_order.lower()
            == "asc"
        ):

            ordering = (
                sort_column.asc()
            )

        else:

            ordering = (
                sort_column.desc()
            )

        # =================================================
        # QUERY
        # =================================================

        statement = (
            select(
                User
            )
            .options(
                selectinload(
                    User.role
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

        users = (
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
                users,

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
    # GET
    # =====================================================

    @staticmethod
    def get_user(
        db: Session,

        user_id: int,
    ) -> User:

        statement = (
            select(
                User
            )
            .options(
                selectinload(
                    User.role
                )
            )
            .where(
                User.id
                == user_id
            )
        )

        user = db.scalar(
            statement
        )

        if user is None:

            raise LookupError(
                "Usuario no encontrado"
            )

        return user

    # =====================================================
    # VALIDAR ROLE
    # =====================================================

    @staticmethod
    def get_valid_role(
        db: Session,

        role_id: int,
    ) -> Role:

        role = db.scalar(
            select(
                Role
            ).where(
                Role.id
                == role_id,

                Role.is_active
                .is_(
                    True
                ),
            )
        )

        if role is None:

            raise ValueError(
                "El rol seleccionado no existe "
                "o está desactivado"
            )

        return role

    # =====================================================
    # VALIDAR EMAIL
    # =====================================================

    @staticmethod
    def validate_unique_email(
        db: Session,

        email: str,

        exclude_user_id:
            int | None = None,
    ) -> None:

        statement = (
            select(
                User
            )
            .where(
                User.email
                == email
            )
        )

        if exclude_user_id is not None:

            statement = (
                statement.where(
                    User.id
                    != exclude_user_id
                )
            )

        existing = db.scalar(
            statement
        )

        if existing is not None:

            raise ValueError(
                "El correo ya está registrado"
            )

    # =====================================================
    # VALIDAR USERNAME
    # =====================================================

    @staticmethod
    def validate_unique_username(
        db: Session,

        username:
            str | None,

        exclude_user_id:
            int | None = None,
    ) -> None:

        if not username:

            return

        statement = (
            select(
                User
            )
            .where(
                User.username
                == username
            )
        )

        if exclude_user_id is not None:

            statement = (
                statement.where(
                    User.id
                    != exclude_user_id
                )
            )

        existing = db.scalar(
            statement
        )

        if existing is not None:

            raise ValueError(
                "El nombre de usuario "
                "ya está registrado"
            )

    # =====================================================
    # VALIDAR DOCUMENT
    # =====================================================

    @staticmethod
    def validate_unique_document(
        db: Session,

        document_number:
            str | None,

        exclude_user_id:
            int | None = None,
    ) -> None:

        if not document_number:

            return

        statement = (
            select(
                User
            )
            .where(
                User.document_number
                == document_number
            )
        )

        if exclude_user_id is not None:

            statement = (
                statement.where(
                    User.id
                    != exclude_user_id
                )
            )

        existing = db.scalar(
            statement
        )

        if existing is not None:

            raise ValueError(
                "El número de documento "
                "ya está registrado"
            )

    # =====================================================
    # CREATE
    # =====================================================

    @staticmethod
    def create_user(
        db: Session,

        data: UserCreate,

        current_user_id:
            int | None = None,

        tenant_id: int | None = None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> User:

        email = (
            data.email
            .strip()
            .lower()
        )

        username = (
            data.username.strip()
            if data.username
            else None
        )

        document_number = (
            data.document_number.strip()
            if data.document_number
            else None
        )

        # =================================================
        # VALIDACIONES
        # =================================================

        UserService.validate_unique_email(
            db=db,

            email=email,
        )

        UserService.validate_unique_username(
            db=db,

            username=username,
        )

        UserService.validate_unique_document(
            db=db,

            document_number=
                document_number,
        )

        role = (
            UserService.get_valid_role(
                db=db,

                role_id=
                    data.role_id,
            )
        )

        # Los usuarios creados desde el panel del tenant deben ser propios.
        if tenant_id is None:
            raise ValueError("No se pudo identificar la empresa del administrador")

        # No se puede crear una identidad de plataforma desde un tenant.
        if role.name.upper() in {"SUPER_ADMIN", "TENANT_ADMIN"}:
            raise ValueError("Este rol solo puede ser asignado por la administracion de plataforma")

        # Validación previa al INSERT; la función bloquea la fila tenant
        # hasta el COMMIT, incluso si dos administradores actúan a la vez.
        enforce_staff_capacity(
            db, tenant_id,
            added_staff=bool(data.is_active and role.name.upper() in INTERNAL_STAFF_ROLES),
        )

        # =================================================
        # USER
        # =================================================

        user = User(
            tenant_id=tenant_id,
            username=
                username,

            first_name=
                data.first_name.strip(),

            last_name=(
                data.last_name.strip()
                if data.last_name
                else None
            ),

            email=
                email,

            phone=(
                data.phone.strip()
                if data.phone
                else None
            ),

            document_number=
                document_number,

            address=(
                data.address.strip()
                if data.address
                else None
            ),

            date_of_birth=
                data.date_of_birth,

            password_hash=
                hash_password(
                    data.password
                ),

            google_id=
                None,

            photo_url=
                None,

            role_id=
                role.id,

            is_active=
                data.is_active,

            is_verified=
                data.is_verified,

            profile_completed=
                data.profile_completed,

            last_login_at=
                None,
        )

        db.add(
            user
        )

        try:

            # Necesitamos el ID antes del commit.
            db.flush()

            # =================================================
            # BITÁCORA
            # =================================================

            AuditLogService.log(
                db=db,

                user_id=
                    current_user_id,

                action=
                    "CREATE_USER",

                module=
                    "USERS",

                entity_type=
                    "User",

                entity_id=
                    user.id,

                description=(
                    f"Se creó el usuario "
                    f"{user.email}"
                ),

                old_values=
                    None,

                new_values=
                    UserService.user_snapshot(
                        user
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
            user
        )

        return (
            UserService.get_user(
                db=db,

                user_id=
                    user.id,
            )
        )

    # =====================================================
    # UPDATE
    # =====================================================

    @staticmethod
    def update_user(
        db: Session,

        user_id: int,

        data: UserUpdate,

        current_user_id:
            int | None = None,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> User:

        user = (
            UserService.get_user(
                db=db,

                user_id=
                    user_id,
            )
        )

        # =================================================
        # SNAPSHOT ANTES
        # =================================================

        old_values = (
            UserService.user_snapshot(
                user
            )
        )

        payload = (
            data.model_dump(
                exclude_unset=True
            )
        )

        # =================================================
        # EMAIL
        # =================================================

        if "email" in payload:

            if not payload["email"]:

                raise ValueError(
                    "El correo es obligatorio"
                )

            email = (
                payload["email"]
                .strip()
                .lower()
            )

            UserService.validate_unique_email(
                db=db,

                email=email,

                exclude_user_id=
                    user.id,
            )

            user.email = email

        # =================================================
        # USERNAME
        # =================================================

        if "username" in payload:

            username = (
                payload["username"]
                .strip()
                if payload["username"]
                else None
            )

            UserService.validate_unique_username(
                db=db,

                username=
                    username,

                exclude_user_id=
                    user.id,
            )

            user.username = username

        # =================================================
        # DOCUMENT
        # =================================================

        if "document_number" in payload:

            document_number = (
                payload["document_number"]
                .strip()
                if payload["document_number"]
                else None
            )

            UserService.validate_unique_document(
                db=db,

                document_number=
                    document_number,

                exclude_user_id=
                    user.id,
            )

            user.document_number = document_number

        # =================================================
        # ROLE
        # =================================================

        if "role_id" in payload:

            role = (
                UserService.get_valid_role(
                    db=db,

                    role_id=
                        payload["role_id"],
                )
            )

            user.role_id = role.id

        # =================================================
        # PASSWORD
        # =================================================

        password_changed = False

        if (
            "password" in payload
            and payload["password"]
        ):

            user.password_hash = (
                hash_password(
                    payload["password"]
                )
            )

            password_changed = True

        # =================================================
        # FIRST NAME
        # =================================================

        if "first_name" in payload:

            if not payload["first_name"]:

                raise ValueError(
                    "El nombre es obligatorio"
                )

            user.first_name = (
                payload["first_name"]
                .strip()
            )

        # =================================================
        # LAST NAME
        # =================================================

        if "last_name" in payload:

            user.last_name = (
                payload["last_name"]
                .strip()
                if payload["last_name"]
                else None
            )

        # =================================================
        # PHONE
        # =================================================

        if "phone" in payload:

            user.phone = (
                payload["phone"]
                .strip()
                if payload["phone"]
                else None
            )

        # =================================================
        # ADDRESS
        # =================================================

        if "address" in payload:

            user.address = (
                payload["address"]
                .strip()
                if payload["address"]
                else None
            )

        # =================================================
        # DATE OF BIRTH
        # =================================================

        if "date_of_birth" in payload:

            user.date_of_birth = (
                payload["date_of_birth"]
            )

        # =================================================
        # STATE
        # =================================================

        if "is_active" in payload:

            user.is_active = (
                payload["is_active"]
            )

        if "is_verified" in payload:

            user.is_verified = (
                payload["is_verified"]
            )

        if "profile_completed" in payload:

            user.profile_completed = (
                payload[
                    "profile_completed"
                ]
            )

        # No permitir que una edición use el rol de plataforma o sobrepase
        # el cupo al reactivar / promover una cuenta existente.
        old_role = db.get(Role, old_values["role_id"]) if old_values.get("role_id") else None
        previous_staff = bool(old_values.get("is_active") and old_role and old_role.name.upper() in INTERNAL_STAFF_ROLES)
        next_role = db.get(Role, user.role_id)
        if next_role and next_role.name.upper() == "SUPER_ADMIN":
            raise ValueError("No se puede asignar SUPER_ADMIN desde el panel de una empresa")
        if next_role and next_role.name.upper() == "TENANT_ADMIN" and (not old_role or old_role.name.upper() != "TENANT_ADMIN"):
            raise ValueError("Solo la plataforma puede asignar TENANT_ADMIN")
        next_staff = bool(user.is_active and next_role and next_role.name.upper() in INTERNAL_STAFF_ROLES)
        if user.tenant_id is None:
            raise ValueError("El usuario no pertenece a ninguna empresa")
        enforce_staff_capacity(
            db, user.tenant_id,
            added_staff=next_staff and not previous_staff,
            exclude_user_id=user.id,
        )

        # =================================================
        # SAVE + BITÁCORA
        # =================================================

        try:

            db.flush()

            new_values = (
                UserService.user_snapshot(
                    user
                )
            )

            if password_changed:

                new_values[
                    "password_changed"
                ] = True

            AuditLogService.log(
                db=db,

                user_id=
                    current_user_id,

                action=
                    "UPDATE_USER",

                module=
                    "USERS",

                entity_type=
                    "User",

                entity_id=
                    user.id,

                description=(
                    f"Se actualizó el usuario "
                    f"{user.email}"
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

        except Exception:

            db.rollback()

            raise

        db.refresh(
            user
        )

        return (
            UserService.get_user(
                db=db,

                user_id=
                    user.id,
            )
        )

    # =====================================================
    # SOFT DELETE
    # =====================================================

    @staticmethod
    def delete_user(
        db: Session,

        user_id: int,

        current_user_id: int,

        ip_address:
            str | None = None,

        user_agent:
            str | None = None,
    ) -> None:

        user = (
            UserService.get_user(
                db=db,

                user_id=
                    user_id,
            )
        )

        if (
            user.id
            == current_user_id
        ):

            raise ValueError(
                "No puedes desactivar "
                "tu propia cuenta"
            )

        if not user.is_active:

            raise ValueError(
                "El usuario ya está desactivado"
            )

        # =================================================
        # SNAPSHOT ANTES
        # =================================================

        old_values = (
            UserService.user_snapshot(
                user
            )
        )

        # =================================================
        # SOFT DELETE
        # =================================================

        user.is_active = False

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
                    "DEACTIVATE_USER",

                module=
                    "USERS",

                entity_type=
                    "User",

                entity_id=
                    user.id,

                description=(
                    f"Se desactivó el usuario "
                    f"{user.email}"
                ),

                old_values=
                    old_values,

                new_values=
                    UserService.user_snapshot(
                        user
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