"""Build the retrieval pipeline and the answer generator from settings (shared by API and eval).

Models are loaded once per process: BGE-M3 and the reranker each take a few seconds and
~2 GB of RAM.
"""

from functools import lru_cache
from pathlib import Path

from backend.app.config import Provider, Role, Settings, get_settings, role_model
from backend.app.llm import PROVIDERS, ChatModel, LLMClient, ProviderSpec, RateLimiter
from backend.app.rag.corpus import load_chunks
from backend.app.rag.pipeline import PipelineConfig, RAGPipeline
from backend.app.rag.query_rewrite import Glossary, QueryRewriter
from backend.app.rag.retriever import Retriever
from ingestion.models import Chunk


@lru_cache
def chunks() -> list[Chunk]:
    return load_chunks()


@lru_cache
def embedder():
    from backend.app.rag.embedder import BGEM3Embedder

    return BGEM3Embedder(get_settings())


@lru_cache
def reranker():
    from backend.app.rag.reranker import make_reranker

    return make_reranker(get_settings())


@lru_cache
def store():
    from backend.app.rag.store import VectorStore, make_client

    s = get_settings()
    return VectorStore(make_client(s), s.qdrant_collection, s.embedding_dim)


def rerank_cache_path(base: Path, s: Settings) -> Path:
    """Scores depend on the model and its input length: bge-reranker-v2-m3 at 512 tokens keeps
    the original cache file (eval/cache/rerank.tsv); any other setting gets its own file."""
    if s.reranker_model == "BAAI/bge-reranker-v2-m3" and s.reranker_max_length == 512:
        return base
    slug = s.reranker_model.split("/")[-1]
    return base.with_name(f"{base.stem}-{slug}-{s.reranker_max_length}{base.suffix}")


def llm_client(settings: Settings, provider: Provider, cache_path: Path | None = None) -> LLMClient:
    """A client for one provider, with the key, rate limits and model fallbacks from settings."""
    s = settings
    if provider == "gemini":
        key = s.gemini_api_key
        spec = ProviderSpec(
            "gemini",
            s.gemini_base_url,
            s.gemini_requests_per_minute,
            s.gemini_requests_per_day,
            max_tokens_field=PROVIDERS["gemini"].max_tokens_field,
            max_retries=PROVIDERS["gemini"].max_retries,
            first_retry_delay=PROVIDERS["gemini"].first_retry_delay,
        )
    else:
        key = s.groq_api_key
        spec = ProviderSpec(
            "groq", s.groq_base_url, s.groq_requests_per_minute,
            extra_body=PROVIDERS["groq"].extra_body,
        )  # fmt: skip
    limiter = RateLimiter(spec.requests_per_minute, spec.requests_per_day)
    return LLMClient(
        key.get_secret_value() if key else None,
        spec,
        cache_path=cache_path,
        fallbacks=s.model_fallbacks,
        limiter=limiter,
    )


class LLMClients:
    """One client per provider, shared by the roles (answer, rewrite, judges) that use it, so a
    provider's rate limit is respected across roles."""

    def __init__(self, settings: Settings, cache_path: Path | None = None) -> None:
        self.settings, self.cache_path = settings, cache_path
        self._clients: dict[str, LLMClient] = {}

    def provider(self, provider: Provider) -> LLMClient:
        if provider not in self._clients:
            self._clients[provider] = llm_client(self.settings, provider, self.cache_path)
        return self._clients[provider]

    def for_role(self, role: Role) -> tuple[LLMClient, str]:
        provider, model = role_model(self.settings, role)
        return self.provider(provider), model


def build_pipeline(
    config: PipelineConfig,
    *,
    settings: Settings | None = None,
    llm: "LLMClients | ChatModel | None" = None,
    rerank_cache: Path | None = None,
) -> RAGPipeline:
    s = settings or get_settings()
    retriever = Retriever(
        chunks(),
        "hybrid",
        store=store(),
        embedder=embedder(),
        candidates=s.candidates_per_retriever,
        rrf_k=s.rrf_k,
        tax_year=s.current_tax_year,
    )
    rewrite_llm, rewrite_model = llm, s.rewrite_model
    if isinstance(llm, LLMClients):
        rewrite_llm, rewrite_model = llm.for_role("rewrite")
    rewriter = QueryRewriter(
        rewrite_llm if config.rewrite != "none" else None,
        rewrite_model,
        Glossary.load(s.glossary_path),
        current_tax_year=s.current_tax_year,
    )
    rr = None
    if config.rerank:
        from backend.app.rag.reranker import CachedReranker

        rr = reranker()
        if rerank_cache:
            rr = CachedReranker(rr, rerank_cache_path(rerank_cache, s))
    return RAGPipeline(chunks(), retriever, rewriter, rr, config)
