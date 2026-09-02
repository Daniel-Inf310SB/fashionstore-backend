from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Sonelya API"
    app_version: str = "0.1.0"

    database_url: str

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
    brevo_sender_name: str = "Sonelya"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


settings = Settings()