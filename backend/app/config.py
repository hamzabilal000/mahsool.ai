"""Application settings. Every model id and endpoint lives here, loaded from env / `.env`."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    reranker_max_length: int = 512  # 27 s vs 37 s per 30 pairs on 4 CPU cores (DECISIONS D26)
    reranker_batch_size: int = 8
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
    rerank_candidates: int = 30  # fused chunks passed to the reranker
    # "max": the reranker also scores each chunk against the first English rewrite and keeps the
    # higher score; chosen on the dev split (DECISIONS D40). Doubles the reranker time.
    rerank_query: Literal["original", "max"] = "max"
    answer_top_k: int = 6  # reranked chunks shown to the answer model
    # Refuse without calling the answer model when the best reranker score is below this.
    # Kept very low: on the dev split Urdu / Roman Urdu questions that *are* answerable often
    # score below 0.01, two of them below 0.001 (DECISIONS D27, D34).
    refusal_threshold: float = 0.0005
    glossary_path: Path = Path("data/glossary_ur.csv")
    groq_base_url: str = "https://api.groq.com/openai/v1"
    rate_limit_per_minute: int = 20  # /ask requests per client IP
    current_tax_year: int = 2027

    # --- Storage (hosted Neon Postgres in development; unused until Milestone 4) ---
    database_url: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "MAHSOOL_DATABASE_URL"),
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
