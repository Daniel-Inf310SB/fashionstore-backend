from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.schemas.auth import (
    CompleteProfileRequest,
    ForgotPasswordRequest,
    GoogleLoginRequest,
    LoginRequest,
    LogoutResponse,
    MessageResponse,
    RefreshTokenRequest,
    RegisterRequest,
    RegisterResponse,
    ResendVerificationCodeRequest,
    ResetPasswordRequest,
    TokenResponse,
    UserAuthResponse,
    UsernameAvailabilityResponse,
    VerifyEmailRequest,
    VerifyResetCodeRequest,
DocumentAvailabilityResponse
)
from app.services.auth_service import AuthService


router = APIRouter(
    prefix="/auth",
    tags=["Authentication"],
)


bearer_scheme = HTTPBearer()


# =========================
# BUILD USER RESPONSE
# =========================

def build_user_response(
    user,
) -> UserAuthResponse:

    permissions = sorted(
        permission.code
        for permission in user.role.permissions
        if permission.is_active
    )

    return UserAuthResponse(
        id=user.id,

        username=user.username,

        first_name=user.first_name,
        last_name=user.last_name,

        email=user.email,

        phone=user.phone,
        document_number=user.document_number,
        address=user.address,

        date_of_birth=user.date_of_birth,

        photo_url=user.photo_url,

        role=user.role.name,

        permissions=permissions,

        is_active=user.is_active,
        is_verified=user.is_verified,
        profile_completed=user.profile_completed,
    )


# =========================
# REGISTRO
# =========================

@router.post(
    "/register",
    response_model=RegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
def register(
    data: RegisterRequest,
    db: Session = Depends(get_db),
):
    try:
        user = AuthService.register(
            db=db,
            data=data,
        )

        return RegisterResponse(
            message=(
                "Cuenta creada. "
                "Te enviamos un código de verificación."
            ),
            email=user.email,
        )

    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EMAIL_NOT_VERIFIED",
                "message": str(error),
            },
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "EMAIL_ALREADY_EXISTS",
                "message": str(error),
            },
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        )


# =========================
# VERIFICAR EMAIL
# =========================

@router.post(
    "/verify-email",
    response_model=MessageResponse,
)
def verify_email(
    data: VerifyEmailRequest,
    db: Session = Depends(get_db),
):
    try:
        AuthService.verify_email(
            db=db,
            email=data.email,
            code=data.code,
        )

        return MessageResponse(
            message=(
                "Correo verificado correctamente"
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )


# =========================
# REENVIAR CÓDIGO
# =========================

@router.post(
    "/resend-verification-code",
    response_model=MessageResponse,
)
def resend_verification_code(
    data: ResendVerificationCodeRequest,
    db: Session = Depends(get_db),
):
    try:
        AuthService.resend_verification_code(
            db=db,
            email=data.email,
        )

        return MessageResponse(
            message=(
                "Te enviamos un nuevo código "
                "de verificación"
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )

    except RuntimeError as error:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(error),
        )


# =========================
# OLVIDÉ CONTRASEÑA
# =========================

@router.post(
    "/forgot-password",
    response_model=MessageResponse,
)
def forgot_password(
    data: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    try:
        AuthService.forgot_password(
            db=db,
            email=data.email,
        )

        return MessageResponse(
            message=(
                "Si existe una cuenta asociada "
                "a ese correo, recibirás un código "
                "de recuperación."
            )
        )

    except RuntimeError:
        return MessageResponse(
            message=(
                "Si existe una cuenta asociada "
                "a ese correo, recibirás un código "
                "de recuperación."
            )
        )


# =========================
# VERIFICAR CÓDIGO RESET
# =========================

@router.post(
    "/verify-reset-code",
    response_model=MessageResponse,
)
def verify_reset_code(
    data: VerifyResetCodeRequest,
    db: Session = Depends(get_db),
):
    try:
        AuthService.verify_password_reset_code(
            db=db,
            email=data.email,
            code=data.code,
        )

        return MessageResponse(
            message="Código correcto"
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )


# =========================
# RESTABLECER CONTRASEÑA
# =========================

@router.post(
    "/reset-password",
    response_model=MessageResponse,
)
def reset_password(
    data: ResetPasswordRequest,
    db: Session = Depends(get_db),
):
    try:
        AuthService.reset_password(
            db=db,
            email=data.email,
            code=data.code,
            new_password=data.new_password,
        )

        return MessageResponse(
            message=(
                "Contraseña actualizada correctamente"
            )
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(error),
        )


# =========================
# LOGIN NORMAL
# =========================

@router.post(
    "/login",
    response_model=TokenResponse,
)
def login(
    data: LoginRequest,
    db: Session = Depends(get_db),
):
    try:
        user = AuthService.authenticate(
            db,
            data,
        )

        access_token, refresh_token = (
            AuthService.create_tokens(
                db=db,
                user=user,

                device_id=data.device_id,
                device_name=data.device_name,
                platform=data.platform,
            )
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,

            user=build_user_response(
                user
            ),
        )

    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        )


# =========================
# LOGIN GOOGLE
# =========================

@router.post(
    "/google",
    response_model=TokenResponse,
)
def google_login(
    data: GoogleLoginRequest,
    db: Session = Depends(get_db),
):
    try:
        user = AuthService.authenticate_google(
            db=db,
            data=data,
        )

        access_token, refresh_token = (
            AuthService.create_tokens(
                db=db,
                user=user,

                device_id=data.device_id,
                device_name=data.device_name,
                platform=data.platform,
            )
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,

            user=build_user_response(
                user
            ),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        )


# =========================
# COMPROBAR USERNAME
# =========================

@router.get(
    "/check-username",
    response_model=UsernameAvailabilityResponse,
)
def check_username(
    username: str = Query(
        min_length=3,
        max_length=50,
    ),

    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),

    db: Session = Depends(get_db),
):
    try:
        user = AuthService.get_user_from_access_token(
            db=db,
            access_token=credentials.credentials,
        )

        normalized_username, available, suggestions = (
            AuthService.check_username(
                db=db,
                user=user,
                username=username,
            )
        )

        return UsernameAvailabilityResponse(
            username=normalized_username,
            available=available,
            suggestions=suggestions,
        )

    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        )


# =========================
# COMPLETAR PERFIL
# =========================

@router.post(
    "/complete-profile",
    response_model=UserAuthResponse,
)
def complete_profile(
    data: CompleteProfileRequest,

    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),

    db: Session = Depends(get_db),
):
    try:
        user = AuthService.get_user_from_access_token(
            db=db,
            access_token=credentials.credentials,
        )

        user = AuthService.complete_profile(
            db=db,
            user=user,
            data=data,
        )

        return build_user_response(
            user
        )

    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        )


# =========================
# REFRESH
# =========================

@router.post(
    "/refresh",
    response_model=TokenResponse,
)
def refresh(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    try:
        access_token, user = (
            AuthService.refresh_access_token(
                db=db,
                refresh_token=data.refresh_token,
            )
        )

        return TokenResponse(
            access_token=access_token,

            refresh_token=data.refresh_token,

            user=build_user_response(
                user
            ),
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        )


# =========================
# LOGOUT
# =========================

@router.post(
    "/logout",
    response_model=LogoutResponse,
)
def logout(
    data: RefreshTokenRequest,
    db: Session = Depends(get_db),
):
    try:
        AuthService.logout(
            db=db,
            refresh_token=data.refresh_token,
        )

        return LogoutResponse(
            message="Sesión cerrada correctamente"
        )

    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        )

# =========================
# COMPROBAR DOCUMENTO
# =========================

@router.get(
    "/check-document",
    response_model=DocumentAvailabilityResponse,
)
def check_document(
    document_number: str = Query(
        min_length=1,
        max_length=50,
    ),

    credentials: HTTPAuthorizationCredentials = Depends(
        bearer_scheme
    ),

    db: Session = Depends(get_db),
):
    try:
        user = AuthService.get_user_from_access_token(
            db=db,
            access_token=credentials.credentials,
        )

        normalized_document = (
            document_number
            .strip()
        )

        available = (
            AuthService.is_document_available(
                db=db,
                document_number=normalized_document,
                current_user_id=user.id,
            )
        )

        return DocumentAvailabilityResponse(
            document_number=normalized_document,
            available=available,
        )

    except PermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(error),
        )