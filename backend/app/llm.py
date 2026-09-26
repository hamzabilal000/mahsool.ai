"""Minimal LLM client for OpenAI-compatible chat completions (Groq, Google Gemini) with JSON
output, a rate limiter, retries, model fallbacks and an optional on-disk cache.

The cache makes evaluation reproducible and cheap: every (model, messages) pair is stored in a
JSONL file, so re-running the ablation replays the same LLM outputs without calling the API,
and a run stopped by a daily quota resumes where it stopped.

Which provider and model serves which role (answer, rewrite, judges) is set in
`backend/app/config.py` (DECISIONS D42).
"""

import hashlib
import json
import logging
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx

log = logging.getLogger(__name__)

Provider = Literal["groq", "gemini"]


class LLMError(RuntimeError):
    pass


class ChatModel(Protocol):
    def chat_json(self, model: str, messages: list[dict[str, str]], **kw: Any) -> dict: ...


@dataclass(frozen=True)
class ProviderSpec:
    """How one provider's OpenAI-compatible endpoint differs from the others."""

    name: Provider
    base_url: str
    requests_per_minute: int | None = None
    requests_per_day: int | None = None
    # Groq takes `max_completion_tokens` and can hide the reasoning; Gemini takes `max_tokens`.
    max_tokens_field: str = "max_completion_tokens"
    extra_body: dict = field(default_factory=dict)
    max_retries: int = 6
    first_retry_delay: float = 2.0


GROQ = ProviderSpec(
    "groq",
    "https://api.groq.com/openai/v1",
    requests_per_minute=30,
    extra_body={"include_reasoning": False},
)
GEMINI = ProviderSpec(
    "gemini",
    "https://generativelanguage.googleapis.com/v1beta/openai",
    requests_per_minute=10,
    requests_per_day=20,
    max_tokens_field="max_tokens",
    # Gemini's preview models often answer 503 "high demand" for minutes at a time, and every
    # attempt counts against the 20 requests a day: few retries, spaced out.
    max_retries=4,
    first_retry_delay=30.0,
)
PROVIDERS: dict[str, ProviderSpec] = {"groq": GROQ, "gemini": GEMINI}


class RateLimiter:
    """Client-side request limiter: at most `per_minute` requests in any 60 s window (it waits),
    and at most `per_day` requests per process (it raises, like the provider's daily quota)."""

    def __init__(
        self,
        per_minute: int | None,
        per_day: int | None = None,
        clock=time.monotonic,
        sleep=time.sleep,
    ) -> None:
        self.per_minute, self.per_day = per_minute, per_day
        self.clock, self.sleep = clock, sleep
        self.recent: deque[float] = deque()
        self.today = 0
        self._lock = threading.Lock()

    def acquire(self) -> None:
        with self._lock:
            if self.per_day is not None and self.today >= self.per_day:
                raise LLMError(f"daily limit reached: {self.per_day} requests in this run")
            if self.per_minute:
                while True:
                    now = self.clock()
                    while self.recent and now - self.recent[0] >= 60:
                        self.recent.popleft()
                    if len(self.recent) < self.per_minute:
                        break
                    self.sleep(60 - (now - self.recent[0]) + 0.05)
                self.recent.append(self.clock())
            self.today += 1


def _is_daily_limit(text: str) -> bool:
    # Groq: "... tokens per day (TPD) ..."; Gemini: quotaId "...RequestsPerDayPerProjectPerModel".
    return "per day" in text.lower() or "PerDay" in text


def _is_model_unavailable(status: int, text: str) -> bool:
    # Both providers answer 404 for a model id they do not serve (or no longer serve to new users).
    return status == 404


def _retry_delay(r: httpx.Response) -> float | None:
    if r.headers.get("retry-after"):
        try:
            return float(r.headers["retry-after"])
        except ValueError:
            return None
    m = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', r.text)  # Gemini puts it in the body
    return float(m.group(1)) if m else None


class LLMClient:
    """One provider. `fallbacks` maps a model id to the ids to try, in order, when the provider
    says the model does not exist (e.g. `gemini-3-flash` → `gemini-3-flash-preview`)."""

    def __init__(
        self,
        api_key: str | None,
        provider: ProviderSpec | Provider = GROQ,
        *,
        base_url: str | None = None,
        timeout: float = 90.0,
        cache_path: Path | None = None,
        max_retries: int | None = None,
        fallbacks: dict[str, list[str]] | None = None,
        limiter: RateLimiter | None = None,
    ) -> None:
        self.spec = PROVIDERS[provider] if isinstance(provider, str) else provider
        self.api_key = api_key
        self.base_url = (base_url or self.spec.base_url).rstrip("/")
        self.http = httpx.Client(timeout=timeout)
        self.max_retries = max_retries or self.spec.max_retries
        self.cache_path = cache_path
        self.fallbacks = fallbacks or {}
        self.limiter = limiter or RateLimiter(
            self.spec.requests_per_minute, self.spec.requests_per_day
        )
        self.unavailable: set[str] = set()  # model ids the provider said it does not serve
        # Model ids that hit their daily quota in this process: no further calls until restart,
        # so a run never re-asks after a daily-limit error (cached answers still replay).
        self.exhausted: dict[str, str] = {}
        self._cache: dict[str, dict] = {}
        self._lock = threading.Lock()
        if cache_path and cache_path.exists():
            for line in cache_path.read_text(encoding="utf-8").splitlines():
                row = json.loads(line)
                self._cache[row["key"]] = row["output"]

    @staticmethod
    def _key(model: str, messages: list[dict[str, str]], kw: dict) -> str:
        blob = json.dumps([model, messages, kw], ensure_ascii=False, sort_keys=True)
        return hashlib.sha256(blob.encode()).hexdigest()[:32]

    def candidates(self, model: str) -> list[str]:
        return [model, *self.fallbacks.get(model, [])]

    def resolved_model(self, model: str) -> str:
        """The model id that serves `model` (after fallbacks seen so far in this process)."""
        return next((m for m in self.candidates(model) if m not in self.unavailable), model)

    def cached(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        reasoning_effort: str = "low",
    ) -> dict:
        """The cached answer, without calling the API; KeyError if there is none. A cached
        answer from any candidate model counts: resuming never re-asks a fallback."""
        kw = {"temperature": temperature, "max_tokens": max_tokens, "effort": reasoning_effort}
        for m in self.candidates(model):
            key = self._key(m, messages, kw)
            if key in self._cache:
                return self._cache[key]
        raise KeyError(model)

    def chat_json(
        self,
        model: str,
        messages: list[dict[str, str]],
        *,
        temperature: float = 0.0,
        max_tokens: int = 1024,
        reasoning_effort: str = "low",
    ) -> dict:
        kw = {"temperature": temperature, "max_tokens": max_tokens, "effort": reasoning_effort}
        try:
            return self.cached(model, messages, temperature=temperature, max_tokens=max_tokens,
                               reasoning_effort=reasoning_effort)  # fmt: skip
        except KeyError:
            pass
        if not self.api_key:
            raise LLMError(f"no API key for {self.spec.name}")
        for m in self.candidates(model):
            if m in self.unavailable:
                continue
            if m in self.exhausted:
                raise LLMError(f"daily limit reached earlier in this run: {self.exhausted[m]}")
            body = {
                "model": m,
                "messages": messages,
                "temperature": temperature,
                self.spec.max_tokens_field: max_tokens,
                "response_format": {"type": "json_object"},
                "reasoning_effort": reasoning_effort,
                **self.spec.extra_body,
            }
            try:
                output = self._post(body)
            except LLMError as e:
                if str(e).startswith("daily limit"):
                    self.exhausted[m] = str(e)[:200]
                raise
            if output is None:  # model not served: try the next fallback
                log.warning("%s: model %s is not available, trying the next one", self.spec.name, m)
                self.unavailable.add(m)
                continue
            with self._lock:
                key = self._key(m, messages, kw)
                self._cache[key] = output
                if self.cache_path:
                    self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                    with self.cache_path.open("a", encoding="utf-8") as fh:
                        row = {"key": key, "output": output}
                        fh.write(json.dumps(row, ensure_ascii=False) + "\n")
            return output
        raise LLMError(f"{self.spec.name}: none of {self.candidates(model)} is available")

    def _post(self, body: dict) -> dict | None:
        """The parsed JSON reply, or None if the provider does not serve the model."""
        delay = self.spec.first_retry_delay
        for attempt in range(1, self.max_retries + 1):
            self.limiter.acquire()
            try:
                r = self.http.post(
                    f"{self.base_url}/chat/completions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    json=body,
                )
            except httpx.HTTPError as e:
                err = f"network error: {e}"
            else:
                if r.status_code == 200:
                    choice = r.json()["choices"][0]
                    content = choice["message"].get("content") or ""
                    try:
                        return json.loads(_strip_fence(content))
                    except json.JSONDecodeError:
                        err = f"model returned invalid JSON: {content[:200]!r}"
                elif r.status_code == 429 and _is_daily_limit(r.text):
                    # Daily quota (free tier): it frees up over hours, so retrying is pointless.
                    quota = re.search(r'"quotaValue":\s*"(\d+)"', r.text)
                    per_day = f" ({quota.group(1)} requests per day)" if quota else ""
                    raise LLMError(f"daily limit reached{per_day}: {r.text[:200]}")
                elif _is_model_unavailable(r.status_code, r.text):
                    return None
                elif r.status_code in (429, 500, 502, 503, 504) or (
                    r.status_code == 400 and "json_validate_failed" in r.text
                ):
                    err = f"HTTP {r.status_code}: {r.text[:200]}"
                    wait = _retry_delay(r)
                    if wait:
                        delay = max(delay, wait)
                else:
                    raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
            if attempt == self.max_retries:
                raise LLMError(err)
            log.warning(
                "%s call failed (%s), retry %d in %.0fs", self.spec.name, err, attempt, delay
            )
            time.sleep(delay)
            delay = min(delay * 2, 60)
        raise LLMError("unreachable")


def _strip_fence(text: str) -> str:
    """Gemini sometimes wraps JSON mode output in ```json fences."""
    t = text.strip()
    if t.startswith("```"):
        t = re.sub(r"^```(?:json)?\s*|\s*```$", "", t)
    return t


class GroqClient(LLMClient):
    """Groq client (kept for callers and tests that predate the Gemini provider)."""

    def __init__(self, api_key: str | None, base_url: str = GROQ.base_url, **kw: Any) -> None:
        super().__init__(api_key, GROQ, base_url=base_url, **kw)
