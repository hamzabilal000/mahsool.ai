"""POST /ask and POST /ask/stream — answer a tax question with citations, or refuse;
POST /feedback — thumbs up / down on an answer.

/ask/stream sends server-sent events (DECISIONS D46):
    event: stage   data: {"stage": "search" | "answer"}      progress while the pipeline runs
    event: delta   data: {"text": "..."}                      the answer, a few words at a time
    event: done    data: <envelope, same as POST /ask>
    event: error   data: <envelope with an error code>
The answer text is streamed only after the citation check has passed, so the page never shows
text that is later withdrawn.
"""

import asyncio
import json
import logging
import re
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse, StreamingResponse

from backend.app.db import FeedbackStore
from backend.app.llm import LLMError
from backend.app.models.schemas import AskData, AskRequest, Envelope, FeedbackRequest
from backend.app.service import AskService

log = logging.getLogger(__name__)
router = APIRouter()


class RateLimiter:
    """Sliding-window limit per client IP (in memory; enough for a single instance)."""

    def __init__(self, limit: int, window_s: float = 60.0) -> None:
        self.limit, self.window = limit, window_s
        self.hits: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        now = time.monotonic()
        q = self.hits[key]
        while q and now - q[0] > self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


def get_service(request: Request) -> AskService:
    return request.app.state.service


def get_limiter(request: Request) -> RateLimiter:
    return request.app.state.limiter


def get_store(request: Request) -> FeedbackStore | None:
    return getattr(request.app.state, "store", None)


def envelope_body(*, code: str, error: str | None = None, data=None) -> dict:
    body = Envelope[AskData](success=error is None, data=data, error=error, code=code)
    return body.model_dump(mode="json")


def envelope(status: int, *, code: str, error: str | None = None, data=None) -> JSONResponse:
    return JSONResponse(
        status_code=status, content=envelope_body(code=code, error=error, data=data)
    )


RATE_LIMITED = {"code": "RATE_LIMITED", "error": "Too many questions; try again in a minute."}
LLM_UNAVAILABLE = {"code": "LLM_UNAVAILABLE", "error": "The language model is unavailable."}


def client_key(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def log_ask(store: FeedbackStore | None, question: str, data: AskData) -> AskData:
    """Store the question and answer; the id goes back to the page for feedback."""
    if store is None:
        return data
    try:
        data.id = store.log_ask(question, data)
    except Exception:  # a logging failure must not lose the answer
        log.exception("could not log the question")
    return data


@router.post("/ask", response_model=Envelope[AskData])
async def ask(
    body: AskRequest,
    request: Request,
    service: Annotated[AskService, Depends(get_service)],
    limiter: Annotated[RateLimiter, Depends(get_limiter)],
    store: Annotated[FeedbackStore | None, Depends(get_store)],
) -> JSONResponse:
    if not limiter.allow(client_key(request)):
        return envelope(429, **RATE_LIMITED)
    question = body.question.strip()
    try:
        data = await run_in_threadpool(service.ask, question, body.tax_year)
    except LLMError as e:
        log.warning("LLM unavailable: %s", e)
        return envelope(503, **LLM_UNAVAILABLE)
    data = await run_in_threadpool(log_ask, store, question, data)
    return envelope(200, code="REFUSED" if data.refused else "OK", data=data)


def sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


def text_pieces(text: str, words: int = 4) -> list[str]:
    """The answer in pieces of a few words, keeping every space and newline."""
    tokens = re.findall(r"\S+\s*|\s+", text)
    return ["".join(tokens[i : i + words]) for i in range(0, len(tokens), words)]


@router.post("/ask/stream")
async def ask_stream(
    body: AskRequest,
    request: Request,
    service: Annotated[AskService, Depends(get_service)],
    limiter: Annotated[RateLimiter, Depends(get_limiter)],
    store: Annotated[FeedbackStore | None, Depends(get_store)],
) -> StreamingResponse:
    question = body.question.strip()
    allowed = limiter.allow(client_key(request))

    async def events() -> AsyncIterator[str]:
        if not allowed:
            yield sse("error", envelope_body(**RATE_LIMITED))
            return
        loop = asyncio.get_running_loop()
        stages: asyncio.Queue[str] = asyncio.Queue()

        def on_stage(name: str) -> None:  # called from the worker thread
            loop.call_soon_threadsafe(stages.put_nowait, name)

        task = asyncio.ensure_future(
            run_in_threadpool(service.ask, question, body.tax_year, on_stage)
        )
        while not task.done():
            try:
                stage = await asyncio.wait_for(stages.get(), timeout=0.25)
            except TimeoutError:
                continue
            yield sse("stage", {"stage": stage})
        await asyncio.sleep(0)  # let the last call_soon_threadsafe callbacks run
        while not stages.empty():  # stages sent just before the worker finished
            yield sse("stage", {"stage": stages.get_nowait()})
        try:
            data = task.result()
        except LLMError as e:
            log.warning("LLM unavailable: %s", e)
            yield sse("error", envelope_body(**LLM_UNAVAILABLE))
            return
        except Exception:
            log.exception("unhandled error in /ask/stream")
            yield sse("error", envelope_body(code="INTERNAL_ERROR", error="Internal error"))
            return
        data = await run_in_threadpool(log_ask, store, question, data)
        for piece in text_pieces(data.answer):
            yield sse("delta", {"text": piece})
            await asyncio.sleep(0.02)
        yield sse("done", envelope_body(code="REFUSED" if data.refused else "OK", data=data))

    return StreamingResponse(
        events(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@router.post("/feedback")
async def post_feedback(
    body: FeedbackRequest,
    store: Annotated[FeedbackStore | None, Depends(get_store)],
) -> JSONResponse:
    def reply(status: int, code: str, error: str | None = None, data=None) -> JSONResponse:
        content = {"success": error is None, "data": data, "error": error, "code": code}
        return JSONResponse(status_code=status, content=content)

    if store is None:
        return reply(503, "DB_UNAVAILABLE", "Feedback storage is not configured.")
    comment = (body.comment or "").strip() or None
    found = await run_in_threadpool(store.add_feedback, body.ask_id, body.rating, comment)
    if not found:
        return reply(404, "NOT_FOUND", "Unknown answer id.")
    return reply(200, "OK", data={"ask_id": body.ask_id, "rating": body.rating})
