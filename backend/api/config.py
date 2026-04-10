"""
Application configuration via environment variables.
"""
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://ppm_user:localdev@localhost:5432/productphotomanager"

    # JWT
    jwt_secret: str = "local-dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 480  # 8 hours

    # Storage
    storage_backend: str = "local"  # "local" or "gcs"
    storage_local_path: str = "./storage"
    gcs_bucket: str = ""

    # App
    app_name: str = "ProductPhotoManager"
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Dev mode: skip auth (no login required)
    dev_mode: bool = True

    # Initial admin (created on first run)
    admin_username: str = "admin"
    admin_password: str = "admin1234"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
