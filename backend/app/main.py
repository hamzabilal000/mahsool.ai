"""FastAPI application.

Run locally (no Docker; needs the Qdrant index from `python -m ingestion.index`):
    uvicorn backend.app.main:app --port 8000
Then open http://localhost:8000/docs.
"""

import hashlib
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.app.api.ask import RateLimiter, VisitorDailyLimit
from backend.app.api.ask import router as ask_router
from backend.app.api.eval import router as eval_router
from backend.app.config import get_settings
from backend.app.db import FeedbackStore, database_url

log = logging.getLogger(__name__)


def build_service():
    from backend.app.rag.factory import LLMClients, build_pipeline
    from backend.app.rag.generator import AnswerGenerator
    from backend.app.rag.pipeline import PipelineConfig
    from backend.app.service import AskService

    s = get_settings()
    llm = LLMClients(s, cache_path=s.llm_cache_path)
    config = PipelineConfig(candidates=s.rerank_candidates, rerank_query=s.rerank_query)
    pipeline = build_pipeline(config, settings=s, llm=llm)
    return AskService(
        pipeline,
        AnswerGenerator(*llm.for_role("answer")),
        answer_top_k=s.answer_top_k,
        refusal_threshold=s.refusal_threshold,
        last_tax_year=s.current_tax_year,
    )


def cache_version(service) -> str:
    """Changes whenever anything that shapes an answer changes: prompts, models, retrieval
    settings, or the corpus snapshots. Cached answers from another version are never served."""
    from backend.app.rag.generator import ANSWER_SYSTEM
    from backend.app.rag.query_rewrite import REWRITE_SYSTEM

    s = get_settings()
    snapshots = sorted({c.snapshot_id for c in service.pipeline.by_id.values()})
    parts = [
        ANSWER_SYSTEM, REWRITE_SYSTEM, s.answer_model, s.rewrite_model, s.rerank_query,
        str(s.rerank_candidates), str(s.answer_top_k), str(s.refusal_threshold), *snapshots,
    ]  # fmt: skip
    return hashlib.sha256("\n".join(parts).encode()).hexdigest()[:16]


def build_store() -> FeedbackStore:
    s = get_settings()
    url = s.database_url.get_secret_value() if s.database_url else None
    store = FeedbackStore(database_url(url, s.sqlite_path))
    log.info("question log and feedback in %s", store.kind)
    return store


def create_app(service=None, store=None) -> FastAPI:
    """`service` and `store` can be injected (tests use fakes); otherwise they are built at
    startup."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if getattr(app.state, "store", None) is None:
            app.state.store = build_store()
        if getattr(app.state, "service", None) is None:
            app.state.service = build_service()
        if s.answer_cache and getattr(app.state, "cache_version", None) is None:
            app.state.cache_version = cache_version(app.state.service)
        yield

    s = get_settings()
    app = FastAPI(title="Mahsool AI", version="0.4.0", lifespan=lifespan)
    app.state.service = service
    app.state.store = store
    app.state.limiter = RateLimiter(s.rate_limit_per_minute)
    app.state.visitors = VisitorDailyLimit(s.daily_questions_per_visitor)
    app.state.global_answers = VisitorDailyLimit(s.daily_answers_global)
    app.state.forwarded_for_hops = s.forwarded_for_hops
    app.state.cache_version = None
    app.add_middleware(
        CORSMiddleware,
        allow_origins=s.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type"],
    )
    app.include_router(ask_router)
    app.include_router(eval_router)

    @app.exception_handler(RequestValidationError)
    async def validation_error(_: Request, exc: RequestValidationError) -> JSONResponse:
        msg = "; ".join(f"{'.'.join(map(str, e['loc'][1:]))}: {e['msg']}" for e in exc.errors())
        return JSONResponse(
            status_code=422,
            content={"success": False, "data": None, "error": msg, "code": "VALIDATION_ERROR"},
        )

    @app.exception_handler(Exception)
    async def internal_error(_: Request, exc: Exception) -> JSONResponse:
        log.exception("unhandled error", exc_info=exc)
        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "data": None,
                "error": "Internal error",
                "code": "INTERNAL_ERROR",
            },
        )

    @app.get("/health")
    async def health() -> dict:
        return {"success": True, "data": {"status": "ok"}, "error": None, "code": "OK"}

    return app


app = create_app()
