"""POST /ask — answer a tax question with citations, or refuse."""

import logging
import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import APIRouter, Depends, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse

from backend.app.llm import LLMError
from backend.app.models.schemas import AskData, AskRequest, Envelope
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


def envelope(status: int, *, code: str, error: str | None = None, data=None) -> JSONResponse:
    body = Envelope[AskData](success=error is None, data=data, error=error, code=code)
    return JSONResponse(status_code=status, content=body.model_dump(mode="json"))


@router.post("/ask", response_model=Envelope[AskData])
async def ask(
    body: AskRequest,
    request: Request,
    service: Annotated[AskService, Depends(get_service)],
    limiter: Annotated[RateLimiter, Depends(get_limiter)],
) -> JSONResponse:
    client = request.client.host if request.client else "unknown"
    if not limiter.allow(client):
        return envelope(
            429, code="RATE_LIMITED", error="Too many questions; try again in a minute."
        )
    try:
        data = await run_in_threadpool(service.ask, body.question.strip(), body.tax_year)
    except LLMError as e:
        log.warning("LLM unavailable: %s", e)
        return envelope(503, code="LLM_UNAVAILABLE", error="The language model is unavailable.")
    return envelope(200, code="REFUSED" if data.refused else "OK", data=data)
