"""Gateway configuration loaded from environment variables."""

import os
from pathlib import Path

from pydantic_settings import BaseSettings


def _find_env_file() -> str | None:
    """Search for the .env file in several likely locations."""
    candidates = [
        # Absolute project root (hardcoded for this workspace)
        Path("d:/00 WorkSpace/00CanvasMLStudio/.env"),
        # Relative from project root (when CWD is project root)
        Path(".env"),
        # Relative from services/gateway/
        Path("../../.env"),
        # Relative from services/gateway/app/
        Path("../../../.env"),
    ]
    for p in candidates:
        resolved = p.resolve()
        if resolved.is_file():
            return str(resolved)
    return None


class Settings(BaseSettings):
    """Application settings — reads from .env or environment."""

    # Database
    database_url: str = "postgresql://canvasml:canvasml_dev_2024@localhost:5432/canvasml"

    @property
    def async_database_url(self) -> str:
        """Returns the asyncpg connection string."""
        return self.database_url.replace("postgresql://", "postgresql+asyncpg://")

    # JWT
    jwt_secret_key: str = "dev-secret-change-in-production"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 60

    # CORS
    cors_origins: str = "http://localhost:3000,http://localhost:5173"

    # Server
    gateway_port: int = 8000
    environment: str = "development"

    # LLM / RAG
    google_api_key: str = ""

    model_config = {
        "env_file": _find_env_file() or ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


settings = Settings()
