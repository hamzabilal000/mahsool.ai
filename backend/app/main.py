"""FastAPI application.

Run locally (no Docker; needs the Qdrant index from `python -m ingestion.index`):
    uvicorn backend.app.main:app --port 8000
Then open http://localhost:8000/docs.
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from backend.app.api.ask import RateLimiter, router
from backend.app.config import get_settings

log = logging.getLogger(__name__)


def build_service():
    from backend.app.rag.factory import build_pipeline, groq_client
    from backend.app.rag.generator import AnswerGenerator
    from backend.app.rag.pipeline import PipelineConfig
    from backend.app.service import AskService

    s = get_settings()
    llm = groq_client(s)
    pipeline = build_pipeline(PipelineConfig(candidates=s.rerank_candidates), settings=s, llm=llm)
    return AskService(
        pipeline,
        AnswerGenerator(llm, s.answer_model),
        answer_top_k=s.answer_top_k,
        refusal_threshold=s.refusal_threshold,
        last_tax_year=s.current_tax_year,
    )


def create_app(service=None) -> FastAPI:
    """`service` can be injected (tests use a fake); otherwise it is built at startup."""

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if getattr(app.state, "service", None) is None:
            app.state.service = build_service()
        yield

    app = FastAPI(title="Mahsool AI", version="0.3.0", lifespan=lifespan)
    app.state.service = service
    app.state.limiter = RateLimiter(get_settings().rate_limit_per_minute)
    app.include_router(router)

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
