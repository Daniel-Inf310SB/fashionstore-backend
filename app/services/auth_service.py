import re
import secrets
import unicodedata

from datetime import (
    datetime,
    timedelta,
    timezone,
)

from google.auth.transport import requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    hash_password,
    verify_password,
)
from app.models.email_verification_code import (
    EmailVerificationCode,
)
from app.models.password_reset_code import (
    PasswordResetCode,
)

from app.models.role import Role
from app.models.user import User
from app.models.user_session import UserSession
from app.schemas.auth import (
    CompleteProfileRequest,
    GoogleLoginRequest,
    LoginRequest,
    RegisterRequest,
)
from app.services.email_service import EmailService


class AuthService:

    VERIFICATION_CODE_EXPIRE_MINUTES = 10

    VERIFICATION_CODE_MAX_ATTEMPTS = 5

    VERIFICATION_RESEND_COOLDOWN_SECONDS = 60

    PASSWORD_RESET_EXPIRE_MINUTES = 10

    PASSWORD_RESET_MAX_ATTEMPTS = 5

    PASSWORD_RESET_RESEND_COOLDOWN_SECONDS = 60

    # =========================
    # GENERAR CÓDIGO
    # =========================

    @staticmethod
    def generate_verification_code() -> str:

        return str(
            secrets.randbelow(
                900000
            ) + 100000
        )


    # =========================
    # NORMALIZAR DATETIME
    # =========================

    @staticmethod
    def _ensure_utc(
        value: datetime,
    ) -> datetime:

        if value.tzinfo is None:
            return value.replace(
                tzinfo=timezone.utc,
            )

        return value.astimezone(
            timezone.utc
        )


    # =========================
    # INVALIDAR CÓDIGOS
    # =========================

    @staticmethod
    def _invalidate_active_codes(
        db: Session,
        user_id: int,
    ) -> None:

        now = datetime.now(
            timezone.utc
        )

        active_codes = db.scalars(
            select(
                EmailVerificationCode
            ).where(
                EmailVerificationCode.user_id
                == user_id,

                EmailVerificationCode.used_at
                .is_(None),
            )
        ).all()


        for verification_code in active_codes:
            verification_code.used_at = now


    # =========================
    # CREAR Y ENVIAR CÓDIGO
    # =========================

    @staticmethod
    def _create_and_send_verification_code(
        db: Session,
        user: User,
    ) -> None:

        AuthService._invalidate_active_codes(
            db=db,
            user_id=user.id,
        )


        plain_code = (
            AuthService.generate_verification_code()
        )


        now = datetime.now(
            timezone.utc
        )


        verification_code = (
            EmailVerificationCode(
                user_id=user.id,

                code_hash=hash_password(
                    plain_code
                ),

                attempts=0,

                expires_at=(
                    now
                    + timedelta(
                        minutes=(
                            AuthService
                            .VERIFICATION_CODE_EXPIRE_MINUTES
                        )
                    )
                ),

                used_at=None,
            )
        )


        db.add(
            verification_code
        )

        db.commit()

        db.refresh(
            verification_code
        )


        try:
            EmailService.send_verification_code(
                email=user.email,

                first_name=user.first_name,

                code=plain_code,
            )

        except Exception as error:
            verification_code.used_at = (
                datetime.now(
                    timezone.utc
                )
            )

            db.commit()

            raise RuntimeError(
                "La cuenta fue creada, pero no pudimos "
                "enviar el código de verificación. "
                "Intenta reenviar el código."
            ) from error

    # =========================
    # INVALIDAR CÓDIGOS RESET
    # =========================

    @staticmethod
    def _invalidate_password_reset_codes(
        db: Session,
        user_id: int,
    ) -> None:

        now = datetime.now(
            timezone.utc
        )

        active_codes = db.scalars(
            select(
                PasswordResetCode
            ).where(
                PasswordResetCode.user_id
                == user_id,

                PasswordResetCode.used_at
                .is_(None),
            )
        ).all()

        for reset_code in active_codes:
            reset_code.used_at = now


    # =========================
    # CREAR CÓDIGO RESET
    # =========================

    @staticmethod
    def _create_password_reset_code(
        db: Session,
        user: User,
    ) -> None:

        AuthService._invalidate_password_reset_codes(
            db=db,
            user_id=user.id,
        )

        plain_code = (
            AuthService.generate_verification_code()
        )

        now = datetime.now(
            timezone.utc
        )

        reset_code = PasswordResetCode(
            user_id=user.id,

            code_hash=hash_password(
                plain_code
            ),

            attempts=0,

            expires_at=(
                now
                + timedelta(
                    minutes=(
                        AuthService
                        .PASSWORD_RESET_EXPIRE_MINUTES
                    )
                )
            ),

            used_at=None,
        )

        db.add(
            reset_code
        )

        db.commit()

        db.refresh(
            reset_code
        )

        try:
            EmailService.send_password_reset_code(
                email=user.email,
                first_name=user.first_name,
                code=plain_code,
            )

        except Exception as error:
            reset_code.used_at = (
                datetime.now(
                    timezone.utc
                )
            )

            db.commit()

            raise RuntimeError(
                "No pudimos enviar el código "
                "de recuperación. Intenta nuevamente."
            ) from error


    # =========================
    # OLVIDÉ CONTRASEÑA
    # =========================

    @staticmethod
    def forgot_password(
        db: Session,
        email: str,
    ) -> None:

        normalized_email = (
            email
            .strip()
            .lower()
        )

        user = db.scalar(
            select(
                User
            ).where(
                User.email
                == normalized_email
            )
        )

        # No revelamos si el correo existe.
        if user is None:
            return

        if not user.is_active:
            return

        if not user.is_verified:
            return

        # Cuenta exclusivamente de Google.
        if user.password_hash is None:
            return

        last_code = db.scalar(
            select(
                PasswordResetCode
            )
            .where(
                PasswordResetCode.user_id
                == user.id,

                PasswordResetCode.used_at
                .is_(None),
            )
            .order_by(
                PasswordResetCode
                .created_at
                .desc()
            )
        )

        if last_code is not None:
            created_at = (
                AuthService._ensure_utc(
                    last_code.created_at
                )
            )

            now = datetime.now(
                timezone.utc
            )

            elapsed_seconds = (
                now - created_at
            ).total_seconds()

            cooldown = (
                AuthService
                .PASSWORD_RESET_RESEND_COOLDOWN_SECONDS
            )

            if elapsed_seconds < cooldown:
                return

        AuthService._create_password_reset_code(
            db=db,
            user=user,
        )


    # =========================
    # VERIFICAR CÓDIGO RESET
    # =========================

    @staticmethod
    def verify_password_reset_code(
        db: Session,
        email: str,
        code: str,
    ) -> None:

        normalized_email = (
            email
            .strip()
            .lower()
        )

        user = db.scalar(
            select(
                User
            ).where(
                User.email
                == normalized_email
            )
        )

        if user is None:
            raise ValueError(
                "Código inválido o expirado"
            )

        reset_code = db.scalar(
            select(
                PasswordResetCode
            )
            .where(
                PasswordResetCode.user_id
                == user.id,

                PasswordResetCode.used_at
                .is_(None),
            )
            .order_by(
                PasswordResetCode
                .created_at
                .desc()
            )
        )

        if reset_code is None:
            raise ValueError(
                "Código inválido o expirado"
            )

        now = datetime.now(
            timezone.utc
        )

        expires_at = (
            AuthService._ensure_utc(
                reset_code.expires_at
            )
        )

        if now >= expires_at:
            reset_code.used_at = now

            db.commit()

            raise ValueError(
                "Código inválido o expirado"
            )

        if (
            reset_code.attempts
            >= AuthService
            .PASSWORD_RESET_MAX_ATTEMPTS
        ):
            reset_code.used_at = now

            db.commit()

            raise ValueError(
                "Código inválido o expirado"
            )

        try:
            matches = verify_password(
                code,
                reset_code.code_hash,
            )

        except Exception:
            matches = False

        if not matches:
            reset_code.attempts += 1

            attempts_left = (
                AuthService
                .PASSWORD_RESET_MAX_ATTEMPTS
                - reset_code.attempts
            )

            if attempts_left <= 0:
                reset_code.used_at = now

            db.commit()

            if attempts_left <= 0:
                raise ValueError(
                    "Código inválido o expirado"
                )

            raise ValueError(
                f"Código incorrecto. "
                f"Te quedan {attempts_left} intentos."
            )


    # =========================
    # RESTABLECER CONTRASEÑA
    # =========================

    @staticmethod
    def reset_password(
        db: Session,
        email: str,
        code: str,
        new_password: str,
    ) -> None:

        normalized_email = (
            email
            .strip()
            .lower()
        )

        user = db.scalar(
            select(
                User
            ).where(
                User.email
                == normalized_email
            )
        )

        if user is None:
            raise ValueError(
                "Código inválido o expirado"
            )

        if not user.is_active:
            raise ValueError(
                "Código inválido o expirado"
            )

        AuthService.verify_password_reset_code(
            db=db,
            email=normalized_email,
            code=code,
        )

        reset_code = db.scalar(
            select(
                PasswordResetCode
            )
            .where(
                PasswordResetCode.user_id
                == user.id,

                PasswordResetCode.used_at
                .is_(None),
            )
            .order_by(
                PasswordResetCode
                .created_at
                .desc()
            )
        )

        if reset_code is None:
            raise ValueError(
                "Código inválido o expirado"
            )

        now = datetime.now(
            timezone.utc
        )

        user.password_hash = hash_password(
            new_password
        )

        reset_code.used_at = now

        AuthService._invalidate_password_reset_codes(
            db=db,
            user_id=user.id,
        )

        sessions = db.scalars(
            select(
                UserSession
            ).where(
                UserSession.user_id
                == user.id,

                UserSession.revoked_at
                .is_(None),
            )
        ).all()

        for session in sessions:
            session.revoked_at = now

        db.commit()

        db.refresh(
            user
        )


    # =========================
    # REGISTRO
    # =========================

    @staticmethod
    def register(
        db: Session,
        data: RegisterRequest,
    ) -> User:

        normalized_email = (
            data.email
            .strip()
            .lower()
        )

        existing_user = db.scalar(
            select(
                User
            ).where(
                User.email
                == normalized_email
            )
        )

        if existing_user is not None:

            if existing_user.is_verified:
                raise ValueError(
                    "El correo ya está registrado"
                )

            raise PermissionError(
                "La cuenta existe pero aún no verificaste tu correo"
            )


        normalized_document = None

        if (
            data.document_number
            and data.document_number.strip()
        ):
            normalized_document = (
                data.document_number.strip()
            )

            existing_document = db.scalar(
                select(
                    User
                ).where(
                    User.document_number
                    == normalized_document
                )
            )

            if existing_document is not None:
                raise ValueError(
                    "El documento ya está registrado"
                )


        client_role = db.scalar(
            select(
                Role
            ).where(
                Role.name == "CLIENTE",

                Role.is_active.is_(
                    True
                ),
            )
        )


        if client_role is None:
            raise RuntimeError(
                "El rol CLIENTE no existe. "
                "Ejecuta el seeder."
            )


        user = User(
            username=None,

            first_name=(
                data.first_name
                .strip()
            ),

            last_name=(
                data.last_name.strip()
                if data.last_name
                and data.last_name.strip()
                else None
            ),

            email=normalized_email,

            phone=(
                data.phone.strip()
                if data.phone
                and data.phone.strip()
                else None
            ),

            document_number=(
                normalized_document
            ),

            address=(
                data.address.strip()
                if data.address
                and data.address.strip()
                else None
            ),

            date_of_birth=(
                data.date_of_birth
            ),

            password_hash=hash_password(
                data.password
            ),

            google_id=None,

            photo_url=None,

            role_id=client_role.id,

            is_active=True,

            is_verified=False,

            profile_completed=False,
        )


        db.add(
            user
        )


        try:
            db.commit()

        except IntegrityError:
            db.rollback()

            raise ValueError(
                "No se pudo crear la cuenta. "
                "Verifica que el correo y documento "
                "no estén registrados."
            )


        db.refresh(
            user
        )


        AuthService._create_and_send_verification_code(
            db=db,
            user=user,
        )


        return user


    # =========================
    # VERIFICAR EMAIL
    # =========================

    @staticmethod
    def verify_email(
        db: Session,
        email: str,
        code: str,
    ) -> None:

        normalized_email = (
            email
            .strip()
            .lower()
        )


        user = db.scalar(
            select(
                User
            ).where(
                User.email
                == normalized_email
            )
        )


        if user is None:
            raise ValueError(
                "Código inválido o expirado"
            )


        if user.is_verified:
            raise ValueError(
                "Este correo ya fue verificado"
            )


        verification_code = db.scalar(
            select(
                EmailVerificationCode
            )
            .where(
                EmailVerificationCode.user_id
                == user.id,

                EmailVerificationCode.used_at
                .is_(None),
            )
            .order_by(
                EmailVerificationCode
                .created_at
                .desc()
            )
        )


        if verification_code is None:
            raise ValueError(
                "No existe un código activo. "
                "Solicita uno nuevo."
            )


        now = datetime.now(
            timezone.utc
        )


        expires_at = (
            AuthService._ensure_utc(
                verification_code.expires_at
            )
        )


        if now >= expires_at:
            verification_code.used_at = now

            db.commit()

            raise ValueError(
                "El código expiró. "
                "Solicita uno nuevo."
            )


        if (
            verification_code.attempts
            >= AuthService
            .VERIFICATION_CODE_MAX_ATTEMPTS
        ):
            verification_code.used_at = now

            db.commit()

            raise ValueError(
                "Superaste el número máximo "
                "de intentos. Solicita un código nuevo."
            )


        try:
            matches = verify_password(
                code,
                verification_code.code_hash,
            )

        except Exception:
            matches = False


        if not matches:
            verification_code.attempts += 1


            attempts_left = (
                AuthService
                .VERIFICATION_CODE_MAX_ATTEMPTS
                - verification_code.attempts
            )


            if attempts_left <= 0:
                verification_code.used_at = now

                db.commit()

                raise ValueError(
                    "Código incorrecto. "
                    "Superaste el número máximo "
                    "de intentos. Solicita uno nuevo."
                )


            db.commit()


            raise ValueError(
                f"Código incorrecto. "
                f"Te quedan {attempts_left} intentos."
            )


        verification_code.used_at = now

        user.is_verified = True


        AuthService._invalidate_active_codes(
            db=db,
            user_id=user.id,
        )


        db.commit()

        db.refresh(
            user
        )


    # =========================
    # REENVIAR CÓDIGO
    # =========================

    @staticmethod
    def resend_verification_code(
        db: Session,
        email: str,
    ) -> None:

        normalized_email = (
            email
            .strip()
            .lower()
        )


        user = db.scalar(
            select(
                User
            ).where(
                User.email
                == normalized_email
            )
        )


        if user is None:
            raise ValueError(
                "No existe una cuenta con ese correo"
            )


        if not user.is_active:
            raise ValueError(
                "La cuenta está desactivada"
            )


        if user.is_verified:
            raise ValueError(
                "Este correo ya fue verificado"
            )


        last_code = db.scalar(
            select(
                EmailVerificationCode
            )
            .where(
                EmailVerificationCode.user_id
                == user.id,

                EmailVerificationCode.used_at
                .is_(None),
            )
            .order_by(
                EmailVerificationCode
                .created_at
                .desc()
            )
        )


        if last_code is not None:
            created_at = (
                AuthService._ensure_utc(
                    last_code.created_at
                )
            )


            now = datetime.now(
                timezone.utc
            )


            elapsed_seconds = (
                now - created_at
            ).total_seconds()


            cooldown = (
                AuthService
                .VERIFICATION_RESEND_COOLDOWN_SECONDS
            )


            if elapsed_seconds < cooldown:
                remaining = int(
                    cooldown
                    - elapsed_seconds
                )


                if remaining < 1:
                    remaining = 1


                raise ValueError(
                    f"Espera {remaining} segundos "
                    f"antes de solicitar otro código."
                )


        AuthService._create_and_send_verification_code(
            db=db,
            user=user,
        )


    # =========================
    # LOGIN NORMAL
    # =========================

    @staticmethod
    def authenticate(
        db: Session,
        data: LoginRequest,
    ) -> User:

        normalized_email = (
            data.email
            .strip()
            .lower()
        )


        user = db.scalar(
            select(
                User
            ).where(
                User.email
                == normalized_email
            )
        )


        if user is None:
            raise ValueError(
                "Correo o contraseña incorrectos"
            )


        if user.password_hash is None:
            raise ValueError(
                "Esta cuenta no utiliza contraseña. "
                "Inicia sesión con Google."
            )


        if not verify_password(
            data.password,
            user.password_hash,
        ):
            raise ValueError(
                "Correo o contraseña incorrectos"
            )


        if not user.is_active:
            raise ValueError(
                "La cuenta está desactivada"
            )


        if not user.is_verified:
            raise PermissionError(
                "Debes verificar tu correo "
                "antes de iniciar sesión"
            )


        user.last_login_at = (
            datetime.now(
                timezone.utc
            )
        )


        db.commit()

        db.refresh(
            user
        )


        return user


    # =========================
    # LOGIN GOOGLE
    # =========================

    @staticmethod
    def authenticate_google(
        db: Session,
        data: GoogleLoginRequest,
    ) -> User:

        try:
            google_data = (
                id_token.verify_oauth2_token(
                    data.id_token,

                    requests.Request(),

                    settings.google_client_id,
                )
            )

        except Exception:
            raise ValueError(
                "Token de Google inválido"
            )


        google_id = google_data.get(
            "sub"
        )


        email = google_data.get(
            "email"
        )


        email_verified = google_data.get(
            "email_verified",
            False,
        )


        first_name = (
            google_data.get(
                "given_name"
            )
            or google_data.get(
                "name"
            )
            or "Usuario"
        )


        last_name = google_data.get(
            "family_name"
        )


        photo_url = google_data.get(
            "picture"
        )


        if not google_id or not email:
            raise ValueError(
                "Google no devolvió "
                "los datos necesarios"
            )


        if not email_verified:
            raise ValueError(
                "El correo de Google "
                "no está verificado"
            )


        normalized_email = (
            email
            .strip()
            .lower()
        )


        # =========================
        # EXISTE POR GOOGLE ID
        # =========================

        user = db.scalar(
            select(
                User
            ).where(
                User.google_id
                == google_id
            )
        )


        if user is not None:

            if not user.is_active:
                raise ValueError(
                    "La cuenta está desactivada"
                )


            if photo_url:
                user.photo_url = (
                    photo_url
                )


            user.last_login_at = (
                datetime.now(
                    timezone.utc
                )
            )


            db.commit()

            db.refresh(
                user
            )


            return user


        # =========================
        # EXISTE POR EMAIL
        # =========================

        user = db.scalar(
            select(
                User
            ).where(
                User.email
                == normalized_email
            )
        )


        if user is not None:

            if not user.is_active:
                raise ValueError(
                    "La cuenta está desactivada"
                )


            user.google_id = (
                google_id
            )


            if photo_url:
                user.photo_url = (
                    photo_url
                )


            user.is_verified = True


            AuthService._invalidate_active_codes(
                db=db,
                user_id=user.id,
            )


            user.last_login_at = (
                datetime.now(
                    timezone.utc
                )
            )


            db.commit()

            db.refresh(
                user
            )


            return user


        # =========================
        # NUEVO USUARIO GOOGLE
        # =========================

        client_role = db.scalar(
            select(
                Role
            ).where(
                Role.name == "CLIENTE",

                Role.is_active.is_(
                    True
                ),
            )
        )


        if client_role is None:
            raise RuntimeError(
                "El rol CLIENTE no existe. "
                "Ejecuta el seeder."
            )


        user = User(
            username=None,

            first_name=first_name,

            last_name=last_name,

            email=normalized_email,

            phone=None,

            document_number=None,

            address=None,

            date_of_birth=None,

            password_hash=None,

            google_id=google_id,

            photo_url=photo_url,

            role_id=client_role.id,

            is_active=True,

            is_verified=True,

            profile_completed=False,

            last_login_at=(
                datetime.now(
                    timezone.utc
                )
            ),
        )


        db.add(
            user
        )

        db.commit()

        db.refresh(
            user
        )


        return user


    # =========================
    # USUARIO DESDE ACCESS TOKEN
    # =========================

    @staticmethod
    def get_user_from_access_token(
        db: Session,
        access_token: str,
    ) -> User:

        try:
            payload = decode_token(
                access_token
            )

        except Exception:
            raise PermissionError(
                "Access token inválido o expirado"
            )


        if payload.get(
            "type"
        ) != "access":
            raise PermissionError(
                "El token enviado "
                "no es un access token"
            )


        user_id = payload.get(
            "sub"
        )


        if user_id is None:
            raise PermissionError(
                "Access token inválido"
            )


        try:
            user_id = int(
                user_id
            )

        except (
            TypeError,
            ValueError,
        ):
            raise PermissionError(
                "Access token inválido"
            )


        user = db.scalar(
            select(
                User
            ).where(
                User.id
                == user_id
            )
        )


        if user is None:
            raise PermissionError(
                "El usuario ya no existe"
            )


        if not user.is_active:
            raise PermissionError(
                "La cuenta está desactivada"
            )


        return user


    # =========================
    # NORMALIZAR USERNAME
    # =========================

    @staticmethod
    def normalize_username(
        username: str,
    ) -> str:

        username = (
            username
            .strip()
            .lower()
        )


        username = (
            unicodedata.normalize(
                "NFKD",
                username,
            )
        )


        username = "".join(
            character
            for character in username
            if not unicodedata.combining(
                character
            )
        )


        username = re.sub(
            r"[^a-z0-9._]",
            "",
            username,
        )


        return username


    # =========================
    # USERNAME DISPONIBLE
    # =========================

    @staticmethod
    def is_username_available(
        db: Session,
        username: str,
        current_user_id: int,
    ) -> bool:

        normalized_username = (
            AuthService
            .normalize_username(
                username
            )
        )


        if len(
            normalized_username
        ) < 3:
            return False


        existing_user = db.scalar(
            select(
                User
            ).where(
                User.username
                == normalized_username,

                User.id
                != current_user_id,
            )
        )


        return existing_user is None


    # =========================
    # SUGERIR USERNAMES
    # =========================

    @staticmethod
    def suggest_usernames(
        db: Session,
        user: User,
        requested_username: str,
        limit: int = 4,
    ) -> list[str]:

        requested = (
            AuthService
            .normalize_username(
                requested_username
            )
        )


        first_name = (
            AuthService
            .normalize_username(
                user.first_name
                or ""
            )
        )


        last_name = (
            AuthService
            .normalize_username(
                user.last_name
                or ""
            )
        )


        bases: list[str] = []


        if requested:
            bases.append(
                requested
            )


        if first_name:
            bases.append(
                first_name
            )


        if first_name and last_name:
            bases.append(
                f"{first_name}.{last_name}"
            )

            bases.append(
                f"{first_name}_{last_name}"
            )


        suggestions: list[str] = []

        checked: set[str] = set()


        def try_candidate(
            candidate: str,
        ) -> None:

            candidate = (
                AuthService
                .normalize_username(
                    candidate
                )
            )


            if (
                len(candidate) < 3
                or len(candidate) > 50
                or candidate in checked
            ):
                return


            checked.add(
                candidate
            )


            if (
                AuthService
                .is_username_available(
                    db=db,

                    username=candidate,

                    current_user_id=user.id,
                )
            ):
                suggestions.append(
                    candidate
                )


        for base in bases:
            try_candidate(
                base
            )

            if (
                len(suggestions)
                >= limit
            ):
                break


        suffix = 1


        while (
            len(suggestions) < limit
            and suffix <= 999
        ):
            base = (
                requested
                or first_name
                or "user"
            )


            try_candidate(
                f"{base}_{suffix}"
            )


            suffix += 1


        return suggestions[
            :limit
        ]


    # =========================
    # CHECK USERNAME
    # =========================

    @staticmethod
    def check_username(
        db: Session,
        user: User,
        username: str,
    ) -> tuple[
        str,
        bool,
        list[str],
    ]:

        normalized_username = (
            AuthService
            .normalize_username(
                username
            )
        )


        if len(
            normalized_username
        ) < 3:
            return (
                normalized_username,
                False,
                [],
            )


        available = (
            AuthService
            .is_username_available(
                db=db,

                username=normalized_username,

                current_user_id=user.id,
            )
        )


        suggestions: list[str] = []


        if not available:
            suggestions = (
                AuthService
                .suggest_usernames(
                    db=db,

                    user=user,

                    requested_username=(
                        normalized_username
                    ),
                )
            )


        return (
            normalized_username,
            available,
            suggestions,
        )


    # =========================
    # COMPLETAR PERFIL
    # =========================

    @staticmethod
    def complete_profile(
        db: Session,
        user: User,
        data: CompleteProfileRequest,
    ) -> User:

        normalized_username = (
            AuthService
            .normalize_username(
                data.username
            )
        )


        if len(
            normalized_username
        ) < 3:
            raise ValueError(
                "El nombre de usuario debe "
                "tener al menos 3 caracteres"
            )


        if len(
            normalized_username
        ) > 50:
            raise ValueError(
                "El nombre de usuario no "
                "puede superar 50 caracteres"
            )


        if not re.fullmatch(
            r"[a-z0-9._]+",
            normalized_username,
        ):
            raise ValueError(
                "El nombre de usuario "
                "contiene caracteres inválidos"
            )


        existing_username = db.scalar(
            select(
                User
            ).where(
                User.username
                == normalized_username,

                User.id
                != user.id,
            )
        )


        if existing_username is not None:
            raise ValueError(
                "El nombre de usuario "
                "ya está en uso"
            )


        if data.date_of_birth > (
            datetime.now(
                timezone.utc
            ).date()
        ):
            raise ValueError(
                "La fecha de nacimiento "
                "no es válida"
            )


        if data.document_number is not None:
            normalized_document = (
                data.document_number.strip()
            )

            if normalized_document:
                existing_document = db.scalar(
                    select(
                        User
                    ).where(
                        User.document_number
                        == normalized_document,

                        User.id
                        != user.id,
                    )
                )

                if existing_document is not None:
                    raise ValueError(
                        "El documento ya está registrado"
                    )

                user.document_number = (
                    normalized_document
                )

            else:
                user.document_number = None


        user.username = (
            normalized_username
        )

        user.date_of_birth = (
            data.date_of_birth
        )


        if data.phone is not None:
            user.phone = (
                data.phone.strip()
                if data.phone.strip()
                else None
            )


        if data.address is not None:
            user.address = (
                data.address.strip()
                if data.address.strip()
                else None
            )


        if data.photo_url is not None:
            user.photo_url = (
                data.photo_url.strip()
                if data.photo_url.strip()
                else None
            )


        user.profile_completed = True


        try:
            db.commit()

        except IntegrityError:
            db.rollback()

            raise ValueError(
                "No se pudo completar el perfil. "
                "Verifica que el nombre de usuario "
                "y documento estén disponibles."
            )


        db.refresh(
            user
        )


        return user


    # =========================
    # CREAR TOKENS
    # =========================

    @staticmethod
    def create_tokens(
        db: Session,
        user: User,
        device_id: str | None = None,
        device_name: str | None = None,
        platform: str | None = None,
    ) -> tuple[str, str]:

        access_token = create_access_token(
            subject=user.id,

            extra_claims={
                "role":
                    user.role.name,

                "email":
                    user.email,
            },
        )


        refresh_token = (
            create_refresh_token(
                subject=user.id,
            )
        )


        refresh_token_hashed = (
            hash_password(
                refresh_token
            )
        )


        expires_at = (
            datetime.now(
                timezone.utc
            )
            + timedelta(
                days=(
                    settings
                    .refresh_token_expire_days
                )
            )
        )


        user_session = UserSession(
            user_id=user.id,

            refresh_token_hash=(
                refresh_token_hashed
            ),

            device_id=device_id,

            device_name=device_name,

            platform=platform,

            expires_at=expires_at,

            revoked_at=None,
        )


        db.add(
            user_session
        )

        db.commit()

        db.refresh(
            user_session
        )


        return (
            access_token,
            refresh_token,
        )


    # =========================
    # SESIÓN DESDE REFRESH
    # =========================

    @staticmethod
    def get_session_from_refresh_token(
        db: Session,
        refresh_token: str,
    ) -> tuple[
        User,
        UserSession,
    ]:

        try:
            payload = decode_token(
                refresh_token
            )

        except Exception:
            raise ValueError(
                "Refresh token inválido o expirado"
            )


        if payload.get(
            "type"
        ) != "refresh":
            raise ValueError(
                "El token enviado no "
                "es un refresh token"
            )


        user_id = payload.get(
            "sub"
        )


        if user_id is None:
            raise ValueError(
                "Refresh token inválido"
            )


        try:
            user_id = int(
                user_id
            )

        except (
            TypeError,
            ValueError,
        ):
            raise ValueError(
                "Refresh token inválido"
            )


        user = db.scalar(
            select(
                User
            ).where(
                User.id
                == user_id
            )
        )


        if user is None:
            raise ValueError(
                "El usuario ya no existe"
            )


        if not user.is_active:
            raise ValueError(
                "La cuenta está desactivada"
            )


        now = datetime.now(
            timezone.utc
        )


        sessions = db.scalars(
            select(
                UserSession
            ).where(
                UserSession.user_id
                == user.id,

                UserSession.revoked_at
                .is_(None),

                UserSession.expires_at
                > now,
            )
        ).all()


        for user_session in sessions:

            try:
                token_matches = (
                    verify_password(
                        refresh_token,

                        user_session
                        .refresh_token_hash,
                    )
                )

            except Exception:
                token_matches = False


            if token_matches:
                return (
                    user,
                    user_session,
                )


        raise ValueError(
            "La sesión no existe "
            "o fue cerrada"
        )


    # =========================
    # REFRESH ACCESS TOKEN
    # =========================

    @staticmethod
    def refresh_access_token(
        db: Session,
        refresh_token: str,
    ) -> tuple[
        str,
        User,
    ]:

        user, _ = (
            AuthService
            .get_session_from_refresh_token(
                db,
                refresh_token,
            )
        )


        access_token = (
            create_access_token(
                subject=user.id,

                extra_claims={
                    "role":
                        user.role.name,

                    "email":
                        user.email,
                },
            )
        )


        return (
            access_token,
            user,
        )


    # =========================
    # LOGOUT
    # =========================

    @staticmethod
    def logout(
        db: Session,
        refresh_token: str,
    ) -> None:

        _, user_session = (
            AuthService
            .get_session_from_refresh_token(
                db,
                refresh_token,
            )
        )


        user_session.revoked_at = (
            datetime.now(
                timezone.utc
            )
        )


        db.commit()

    @staticmethod
    def is_document_available(
            db: Session,
            document_number: str,
            current_user_id: int,
    ) -> bool:

        normalized_document = (
            document_number
            .strip()
        )

        existing_user = db.scalar(
            select(User).where(
                User.document_number == normalized_document,
                User.id != current_user_id,
            )
        )

        return existing_user is None
