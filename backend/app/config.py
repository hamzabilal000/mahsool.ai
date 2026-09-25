"""Application settings. Every model id and endpoint lives here, loaded from env / `.env`."""

from functools import lru_cache
from pathlib import Path

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MAHSOOL_", extra="ignore")

    # --- LLMs (Groq) ---
    groq_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("GROQ_API_KEY", "MAHSOOL_GROQ_API_KEY")
    )
    answer_model: str = "openai/gpt-oss-120b"
    rewrite_model: str = "openai/gpt-oss-20b"

    # --- Retrieval models ---
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_batch_size: int = 8
    embedding_max_length: int = 2048  # longest chunk is ~1,300 BGE-M3 tokens (DECISIONS D21)
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    hf_cache_dir: Path | None = None

    # --- Vector store ---
    qdrant_url: str | None = Field(
        default=None, validation_alias=AliasChoices("QDRANT_URL", "MAHSOOL_QDRANT_URL")
    )
    qdrant_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("QDRANT_API_KEY", "MAHSOOL_QDRANT_API_KEY")
    )
    qdrant_path: Path = Path("data/qdrant")  # embedded mode when no URL is set
    qdrant_collection: str = "fbr_laws"

    # --- Retrieval behaviour ---
    rrf_k: int = 60
    candidates_per_retriever: int = 30  # top-N from each of dense and sparse before fusion
    current_tax_year: int = 2027

    # --- Storage (hosted Neon Postgres in development; unused until Milestone 4) ---
    database_url: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "MAHSOOL_DATABASE_URL"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
