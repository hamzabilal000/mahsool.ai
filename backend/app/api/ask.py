"""POST /ask and POST /ask/stream — answer a tax question with citations, or refuse;
POST /feedback — thumbs up / down on an answer.

/ask/stream sends server-sent events (DECISIONS D46):
    event: stage   data: {"stage": "search" | "answer"}      progress while the pipeline runs
    event: delta   data: {"text": "..."}                      the answer, a few words at a time
    event: done    data: <envelope, same as POST /ask>
    event: error   data: <envelope with an error code>
The answer text is streamed only after the citation check has passed, so the page never shows
text that is later withdrawn.

Free-tier demo safeguards (D53), shared by both endpoints through `answer()`:
- repeated questions are served from the answer cache (no LLM quota, no reranking);
- each visitor (client IP) may ask `daily_questions_per_visitor` uncached questions per UTC day,
  and all visitors together get `daily_answers_global` answers that call the answer model (D59);
- when the answer model's daily quota is used up, the reply is a friendly "try again tomorrow"
  message in the question's language (code DAILY_LIMIT), not an error.
"""

import asyncio
import hashlib
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
from backend.app.llm import DailyLimitError, LLMError
from backend.app.models.schemas import AskData, AskRequest, Envelope, FeedbackRequest
from backend.app.rag.query_rewrite import detect_language
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


class VisitorDailyLimit:
    """At most `limit` uncached questions per key per UTC day (in memory, one instance).

    Used per client IP for visitors and with the single key "all" for the global cap."""

    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.day = ""
        self.counts: dict[str, int] = defaultdict(int)

    def _roll(self) -> None:
        today = time.strftime("%Y-%m-%d", time.gmtime())
        if today != self.day:
            self.day, self.counts = today, defaultdict(int)

    def allow(self, key: str) -> bool:
        self._roll()
        return self.limit <= 0 or self.counts[key] < self.limit

    def spend(self, key: str) -> None:
        self._roll()
        self.counts[key] += 1


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
DAILY_LIMIT_TEXT = {
    "en": "Mahsool runs on a free AI quota, and today's quota is used up. Please try again "
    "tomorrow. Questions others have already asked still get an answer.",
    "ur": "محصول مفت اے آئی کوٹے پر چلتا ہے اور آج کا کوٹہ ختم ہو گیا ہے۔ براہِ کرم کل دوبارہ "
    "کوشش کریں۔ جو سوال پہلے پوچھے جا چکے ہیں ان کا جواب اب بھی ملتا ہے۔",
    "roman_ur": "Mahsool free AI quota par chalta hai aur aaj ka quota khatam ho gaya hai. "
    "Meharbani karke kal dobara koshish karein. Jo sawal pehle pooche ja chuke hain un ka "
    "jawab ab bhi milta hai.",
}
VISITOR_LIMIT_TEXT = {
    "en": "You have reached today's limit of new questions for this free demo. Please come back "
    "tomorrow. Questions others have already asked still get an answer.",
    "ur": "آپ اس مفت ڈیمو میں آج کے نئے سوالوں کی حد تک پہنچ گئے ہیں۔ براہِ کرم کل دوبارہ آئیں۔ "
    "جو سوال پہلے پوچھے جا چکے ہیں ان کا جواب اب بھی ملتا ہے۔",
    "roman_ur": "Aap is free demo mein aaj ke naye sawalon ki had tak pohanch gaye hain. "
    "Meharbani karke kal dobara aayein. Jo sawal pehle pooche ja chuke hain un ka jawab ab bhi "
    "milta hai.",
}


class AnswerRefused(Exception):
    """A friendly, expected failure (quota, limits) with an HTTP status and envelope code."""

    def __init__(self, status: int, code: str, error: str) -> None:
        super().__init__(error)
        self.status, self.code, self.error = status, code, error


def client_key(request: Request) -> str:
    hops = getattr(request.app.state, "forwarded_for_hops", 0)
    forwarded = request.headers.get("x-forwarded-for", "")
    if hops > 0 and forwarded:
        entries = [e.strip() for e in forwarded.split(",") if e.strip()]
        if entries:
            return entries[-min(hops, len(entries))]
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


def cache_key(version: str, question: str, tax_year: int | None) -> str:
    norm = re.sub(r"\s+", " ", question.strip().lower()).rstrip(" ?.!؟۔")
    return hashlib.sha256(f"{version}|{tax_year}|{norm}".encode()).hexdigest()


def answer(request: Request, question: str, tax_year: int | None, on_stage=None) -> AskData:
    """Cache → visitor limit → pipeline → cache and log. Runs in a worker thread."""
    app = request.app
    store: FeedbackStore | None = getattr(app.state, "store", None)
    visitors: VisitorDailyLimit | None = getattr(app.state, "visitors", None)
    everyone: VisitorDailyLimit | None = getattr(app.state, "global_answers", None)
    version = getattr(app.state, "cache_version", None)
    key = cache_key(version, question, tax_year) if (store and version) else None
    if key:
        try:
            cached = store.cached_answer(key)
        except Exception:
            log.exception("answer cache read failed")
            cached = None
        if cached is not None:
            cached.timings_ms = {"cache": 1}
            return log_ask(store, question, cached)
    visitor = client_key(request)
    lang = detect_language(question)
    if visitors and not visitors.allow(visitor):
        raise AnswerRefused(429, "VISITOR_DAILY_LIMIT", VISITOR_LIMIT_TEXT[lang])
    if everyone and not everyone.allow("all"):
        raise AnswerRefused(503, "DAILY_LIMIT", DAILY_LIMIT_TEXT[lang])
    try:
        data = app.state.service.ask(question, tax_year, on_stage)
    except DailyLimitError as e:
        log.warning("daily LLM quota used up: %s", e)
        raise AnswerRefused(503, "DAILY_LIMIT", DAILY_LIMIT_TEXT[lang]) from e
    except LLMError as e:
        log.warning("LLM unavailable: %s", e)
        raise AnswerRefused(503, LLM_UNAVAILABLE["code"], LLM_UNAVAILABLE["error"]) from e
    if visitors:
        visitors.spend(visitor)
    if everyone and "answer_llm" in data.timings_ms:  # refused before the answer model: free
        everyone.spend("all")
    if key:
        try:
            store.cache_answer(key, question, data)
        except Exception:
            log.exception("answer cache write failed")
    return log_ask(store, question, data)


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
    try:
        data = await run_in_threadpool(answer, request, body.question.strip(), body.tax_year)
    except AnswerRefused as e:
        return envelope(e.status, code=e.code, error=e.error)
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
            run_in_threadpool(answer, request, question, body.tax_year, on_stage)
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
        except AnswerRefused as e:
            yield sse("error", envelope_body(code=e.code, error=e.error))
            return
        except Exception:
            log.exception("unhandled error in /ask/stream")
            yield sse("error", envelope_body(code="INTERNAL_ERROR", error="Internal error"))
            return
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
