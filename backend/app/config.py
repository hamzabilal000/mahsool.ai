"""Application settings. Every model id and endpoint lives here, loaded from env / `.env`."""

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import AliasChoices, Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

Provider = Literal["groq", "gemini"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_prefix="MAHSOOL_", extra="ignore")

    # --- LLMs: a provider and a model per role (DECISIONS D42) ---
    groq_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("GROQ_API_KEY", "MAHSOOL_GROQ_API_KEY")
    )
    gemini_api_key: SecretStr | None = Field(
        default=None, validation_alias=AliasChoices("GEMINI_API_KEY", "MAHSOOL_GEMINI_API_KEY")
    )
    answer_provider: Provider = "groq"
    answer_model: str = "openai/gpt-oss-120b"
    rewrite_provider: Provider = "groq"
    rewrite_model: str = "openai/gpt-oss-20b"
    # Test-set judges (eval/verify_testset.py): two model families, neither wrote the questions.
    judge1_provider: Provider = "gemini"
    judge1_model: str = "gemini-3-flash"
    judge1_reasoning: str = "low"
    judge2_provider: Provider = "groq"
    judge2_model: str = "qwen/qwen3.8-27b"
    judge2_reasoning: str = "none"  # Qwen's free tier counts thinking tokens (D38)
    # Tried in order when a provider says it does not serve a model id (404). Google serves Gemini 3
    # Flash only as "gemini-3-flash-preview"; gemini-2.5-flash is closed to new API users.
    model_fallbacks: dict[str, list[str]] = {
        "gemini-3-flash": ["gemini-3-flash-preview", "gemini-2.5-flash"],
    }
    # Client-side limits per provider (free tiers; the providers enforce their own as well).
    groq_requests_per_minute: int = 30
    gemini_requests_per_minute: int = 10
    # Google's free tier on this key: 20 requests a day per Flash model, failed calls included
    # (quota GenerateRequestsPerDayPerProjectPerModel-FreeTier, seen 2026-09-25; DECISIONS D42).
    gemini_requests_per_day: int = 20
    gemini_base_url: str = "https://generativelanguage.googleapis.com/v1beta/openai"
    # Development only: replay (and extend) an LLM cache in the API, e.g. eval/cache/groq.jsonl,
    # so test-set questions answer without using the daily quota. Unset in production.
    llm_cache_path: Path | None = None

    # --- Retrieval models ---
    embedding_model: str = "BAAI/bge-m3"
    embedding_dim: int = 1024
    embedding_batch_size: int = 8
    embedding_max_length: int = 2048  # longest chunk is ~1,300 BGE-M3 tokens (DECISIONS D21)
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    reranker_max_length: int = 512  # 27 s vs 37 s per 30 pairs on 4 CPU cores (DECISIONS D26)
    reranker_batch_size: int = 8
    # int8 dynamic quantisation of the reranker's linear layers (CPU speed-up, D52).
    reranker_quantize: bool = False
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
    # Tuned on the dev split for latency (DECISIONS D52): 15 fused chunks go to the reranker, and
    # only Urdu / Roman Urdu questions are also scored against the English rewrite (keeping the
    # higher score, D40). Dev Hit@5 98.0% vs 96.1%, ~2.7x fewer reranker pairs.
    rerank_candidates: int = 15
    rerank_query: Literal["original", "max", "max_non_en"] = "max_non_en"
    answer_top_k: int = 6  # reranked chunks shown to the answer model
    # Refuse without calling the answer model when the best reranker score is below this.
    # Kept very low: on the dev split Urdu / Roman Urdu questions that *are* answerable often
    # score below 0.01, two of them below 0.001 (DECISIONS D27, D34).
    refusal_threshold: float = 0.0005
    glossary_path: Path = Path("data/glossary_ur.csv")
    groq_base_url: str = "https://api.groq.com/openai/v1"
    rate_limit_per_minute: int = 20  # /ask requests per client IP
    # Free-tier demo (D53, D59): new (uncached) questions a visitor (client IP) may ask per UTC
    # day; cached answers do not count. 0 = no limit.
    daily_questions_per_visitor: int = 10
    # All visitors together: answers per UTC day that call the answer model, sized to the free
    # GPT OSS 120B quota (~200k tokens/day at ~3k tokens per answer). 0 = no limit.
    daily_answers_global: int = 60
    # Behind a reverse proxy (the Hugging Face Space), the client IP is the entry this many places
    # from the right of X-Forwarded-For (proxies append, so the leftmost entries can be forged).
    # 0 = use the socket peer address.
    forwarded_for_hops: int = 0
    answer_cache: bool = True  # serve repeated questions from the answer cache (database)
    # The React dev server (Vite); the browser sends cookies (axios withCredentials).
    cors_origins: list[str] = ["http://localhost:5173"]
    current_tax_year: int = 2027

    # --- Storage: question log + feedback ---
    # Question log + feedback: Postgres when DATABASE_URL is set, else this SQLite file (D47).
    sqlite_path: Path = Path("data/mahsool.db")
    database_url: SecretStr | None = Field(
        default=None,
        validation_alias=AliasChoices("DATABASE_URL", "MAHSOOL_DATABASE_URL"),
    )


Role = Literal["answer", "rewrite", "judge1", "judge2"]


def role_model(s: Settings, role: Role) -> tuple[Provider, str]:
    """(provider, model id) configured for a role."""
    return getattr(s, f"{role}_provider"), getattr(s, f"{role}_model")


@lru_cache
def get_settings() -> Settings:
    return Settings()
