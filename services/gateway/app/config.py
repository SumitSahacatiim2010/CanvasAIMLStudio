"""Gateway configuration loaded from environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings — reads from .env or environment."""

    # Database
    database_url: str = "postgresql://canvasml:canvasml_dev_2024@localhost:5432/canvasml"

    # JWT
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Server
    gateway_port: int = 8000
    environment: str = "development"

    model_config = {"env_file": "../../.env", "env_file_encoding": "utf-8"}


settings = Settings()
