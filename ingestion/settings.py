"""Ingestion settings, loaded from environment variables / `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class IngestionSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MAHSOOL_", extra="ignore")

    data_dir: Path = Path("data")
    max_chunk_tokens: int = 800
    http_timeout_s: float = 300.0
    user_agent: str = "mahsool-ai-ingestion/0.1 (+https://github.com/hamzabilal000/mahsool.ai)"

    @property
    def raw_dir(self) -> Path:
        return self.data_dir / "raw"

    @property
    def interim_dir(self) -> Path:
        return self.data_dir / "interim"

    @property
    def processed_dir(self) -> Path:
        return self.data_dir / "processed"


@lru_cache
def get_settings() -> IngestionSettings:
    return IngestionSettings()
