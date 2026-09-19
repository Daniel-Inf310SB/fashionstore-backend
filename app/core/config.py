from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    # =========================
    # APP
    # =========================

    app_name: str = "FashionStore API"
    app_version: str = "0.1.0"

    # =========================
    # DATABASE
    # =========================

    database_url: str

    # =========================
    # GOOGLE
    # =========================

    google_client_id: str

    # =========================
    # JWT
    # =========================

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"

    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 30

    # =========================
    # BREVO
    # =========================

    brevo_api_key: str
    brevo_sender_email: str
    brevo_sender_name: str = "FashionStore"

    # =========================
    # CLOUDINARY
    # =========================

    cloudinary_cloud_name: str
    cloudinary_api_key: str
    cloudinary_api_secret: str

    # =========================
    # STRIPE - MÓDULO 11
    # =========================

    stripe_publishable_key: str = ""
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_currency: str = "bob"

    # =========================
    # OPENAI - MÓDULO 13
    # =========================

    openai_api_key: str = ""
    openai_model: str = "gpt-4.1-mini"
    openai_timeout_seconds: int = 30
    openai_max_retries: int = 2
    openai_retry_base_delay_seconds: float = 0.6
    openai_max_output_tokens: int = 700

    openai_image_model: str = ""
    openai_image_timeout_seconds: int = 120

    ai_recommendation_context_limit: int = 15
    ai_assistant_context_limit: int = 15
    ai_catalog_candidate_pool: int = 60
    ai_report_detail_limit: int = 5

    # =========================
    # EXPIRACIÓN AUTOMÁTICA
    # =========================

    order_payment_ttl_minutes: int = 30
    reservation_ttl_hours: int = 24
    expiration_check_minutes: int = 5
    expiration_scheduler_enabled: bool = True

    # =========================
    # FIREBASE / FCM
    # =========================

    firebase_enabled: bool = False
    firebase_credentials_path: str | None = None

    # =========================
    # COLA DE ENTREGA FCM
    # =========================

    push_jobs_enabled: bool = True

    # Cada cuánto revisar entregas pendientes.
    push_job_interval_seconds: int = 10

    # Cantidad máxima de entregas procesadas por ejecución.
    push_delivery_batch_size: int = 100

    # Reintentos de una entrega fallida.
    push_max_retries: int = 5

    # Tiempo antes de volver a intentar una entrega fallida.
    push_retry_delay_minutes: int = 2

    # =========================
    # CAMPAÑAS MASIVAS
    # =========================

    marketing_notification_jobs_enabled: bool = True

    # Cada cuánto revisar promociones,
    # colecciones y temporadas pendientes.
    marketing_campaign_job_interval_seconds: int = 10

    # Cantidad de campañas procesadas por ejecución.
    marketing_campaign_batch_size: int = 5

    # Cantidad de clientes procesados por lote.
    marketing_customer_batch_size: int = 250

    # Reintentos de una campaña fallida.
    marketing_campaign_max_retries: int = 3

    # Minutos antes de reintentar una campaña fallida.
    marketing_campaign_retry_minutes: int = 5

    # =========================
    # CONFIG
    # =========================

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()