"""Configuração da aplicação (variáveis de ambiente / arquivo .env)."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

PROJECT_ROOT = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=PROJECT_ROOT / ".env", env_file_encoding="utf-8", extra="ignore")

    data_dir: Path = PROJECT_ROOT / "data"
    database_url: str | None = None
    default_seed: int = 42
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173"
    log_level: str = "INFO"

    @property
    def resolved_database_url(self) -> str:
        if self.database_url:
            return self.database_url
        return f"sqlite:///{(self.data_dir / 'synthetic_patients.db').as_posix()}"

    @property
    def generated_dir(self) -> Path:
        return self.data_dir / "generated"

    @property
    def exports_dir(self) -> Path:
        return self.data_dir / "exports"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
