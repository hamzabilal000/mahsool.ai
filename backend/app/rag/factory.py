"""Build the retrieval pipeline and the answer generator from settings (shared by API and eval).

Models are loaded once per process: BGE-M3 and the reranker each take a few seconds and
~2 GB of RAM.
"""

from functools import lru_cache
from pathlib import Path

from backend.app.config import Settings, get_settings
from backend.app.llm import GroqClient
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
    from backend.app.rag.reranker import BGEReranker

    return BGEReranker(get_settings())


@lru_cache
def store():
    from backend.app.rag.store import VectorStore, make_client

    s = get_settings()
    return VectorStore(make_client(s), s.qdrant_collection, s.embedding_dim)


def groq_client(settings: Settings, cache_path: Path | None = None) -> GroqClient:
    key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else None
    return GroqClient(key, base_url=settings.groq_base_url, cache_path=cache_path)


def build_pipeline(
    config: PipelineConfig,
    *,
    settings: Settings | None = None,
    llm: GroqClient | None = None,
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
    rewriter = QueryRewriter(
        llm if config.rewrite != "none" else None,
        s.rewrite_model,
        Glossary.load(s.glossary_path),
        current_tax_year=s.current_tax_year,
    )
    rr = None
    if config.rerank:
        from backend.app.rag.reranker import CachedReranker

        rr = CachedReranker(reranker(), rerank_cache) if rerank_cache else reranker()
    return RAGPipeline(chunks(), retriever, rewriter, rr, config)
