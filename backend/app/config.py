"""Environment-backed application settings. Secrets are never embedded in source files."""
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql+asyncpg://optifreight:change_me@localhost:5432/optifreight"
    JWT_SECRET_KEY: str = Field(default="", min_length=0)
    JWT_SECRET: str = ""
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60
    REGISTRATION_OTP_TTL_MINUTES: int = 10
    REGISTRATION_OTP_MAX_ATTEMPTS: int = 5
    OSRM_URL: str = "http://localhost:5000"
    OSRM_FALLBACK_URL: str = "https://router.project-osrm.org"
    OSRM_TIMEOUT_SECONDS: float = 8.0
    OSRM_MAX_SNAP_DISTANCE_KM: float = 1.0
    # Set true only when OSRM_URL serves a reviewed heavy-goods-vehicle profile.
    # Public/demo car routers must never be treated as truck-route verification.
    OSRM_TRUCK_PROFILE_CONFIRMED: bool = False
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173"
    APP_ENV: str = "development"
    REGULATORY_TRUSTED_SOURCES: str = ""
    # Optional commercial integrations. Keys alone are not sufficient unless the
    # provider implements the documented adapter contract in services/integrations.
    EWAYBILL_API_BASE_URL: str = ""
    EWAYBILL_API_KEY: str = ""
    EWAYBILL_CLIENT_ID: str = ""
    EWAYBILL_CLIENT_SECRET: str = ""
    EWAYBILL_GSTIN: str = ""
    IDENTITY_VERIFICATION_API_BASE_URL: str = ""
    IDENTITY_VERIFICATION_API_KEY: str = ""
    IDENTITY_VERIFICATION_PROVIDER: str = ""
    GOOGLE_MAPS_EMBED_KEY: str = ""
    DOCUMENT_STORAGE_DIR: str = "backend/uploads"
    MAX_DOCUMENT_UPLOAD_MB: int = 12
    DRIVER_REST_MISSED_AFTER_HOURS: int = 24
    DRIVER_AUTO_BLACKLIST: bool = True
    PLATFORM_OWNER_EMAILS: str = ""
    SMS_PROVIDER: str = ""
    SMS_API_BASE_URL: str = ""
    SMS_API_KEY: str = ""
    SMS_SENDER_ID: str = ""
    SMS_TWILIO_ACCOUNT_SID: str = ""
    SMS_TWILIO_AUTH_TOKEN: str = ""
    SMS_TWILIO_MESSAGING_SERVICE_SID: str = ""

    model_config = SettingsConfigDict(
        env_file=str(PROJECT_ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def platform_owner_email_list(self) -> list[str]:
        return [x.strip().lower() for x in self.PLATFORM_OWNER_EMAILS.split(",") if x.strip()]

    @property
    def effective_jwt_secret(self) -> str:
        return self.JWT_SECRET_KEY or self.JWT_SECRET

    @property
    def cors_origin_list(self) -> list[str]:
        return [x.strip() for x in self.CORS_ORIGINS.split(",") if x.strip()]

settings = Settings()
