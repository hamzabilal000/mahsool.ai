"""Per-request stage timings, with rate-limit waiting kept apart from real work (DECISIONS D52).

A `StageTimer` is bound to the current request (a context variable, so it follows the request
into worker threads started with `contextvars.copy_context()` or `run_in_threadpool`). Code marks
stages with `with stage("rerank"):`; the LLM client reports time spent sleeping for its rate
limiter or between retries with `add_wait()`, and time spent waiting for the API with
`add_api()`. The result is a flat dict of milliseconds, e.g.

    {"rewrite": 950, "retrieval": 410, "rerank": 26100, "answer_llm": 3200,
     "citation_check": 1, "llm_wait": 0, "llm_api": 4050, "llm_cached": 1, "total": 30700}

Stages can nest (the rewrite stage contains its LLM call); `llm_wait` + `llm_api` add up the LLM
time across stages, so "compute" for a stage is its time minus the LLM wait inside it.
"""

import time
from collections import defaultdict
from contextlib import contextmanager
from contextvars import ContextVar

_current: ContextVar["StageTimer | None"] = ContextVar("stage_timer", default=None)


class StageTimer:
    def __init__(self) -> None:
        self.ms: dict[str, float] = defaultdict(float)
        self.counts: dict[str, int] = defaultdict(int)
        self.t0 = time.perf_counter()

    def result(self) -> dict[str, int]:
        out = {k: round(v) for k, v in self.ms.items()}
        out.update(self.counts)
        out["total"] = round((time.perf_counter() - self.t0) * 1000)
        return out


@contextmanager
def request_timer():
    """Bind a fresh StageTimer to the current context for the duration of the block."""
    timer = StageTimer()
    token = _current.set(timer)
    try:
        yield timer
    finally:
        _current.reset(token)


@contextmanager
def stage(name: str):
    timer = _current.get()
    t = time.perf_counter()
    try:
        yield
    finally:
        if timer is not None:
            timer.ms[name] += (time.perf_counter() - t) * 1000


def add_wait(seconds: float) -> None:
    """Time slept for a client-side rate limit or a retry back-off (not real work)."""
    timer = _current.get()
    if timer is not None:
        timer.ms["llm_wait"] += seconds * 1000


def add_api(seconds: float) -> None:
    """Time spent waiting for the provider's HTTP response (network + model time)."""
    timer = _current.get()
    if timer is not None:
        timer.ms["llm_api"] += seconds * 1000


def count(name: str) -> None:
    timer = _current.get()
    if timer is not None:
        timer.counts[name] += 1
