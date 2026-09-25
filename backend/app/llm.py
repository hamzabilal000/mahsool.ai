"""Minimal Groq client (OpenAI-compatible chat completions) with JSON output, retries and an
optional on-disk cache.

The cache makes evaluation reproducible and cheap: every (model, messages) pair is stored in a
JSONL file, so re-running the ablation replays the same LLM outputs without calling Groq.
"""

import hashlib
import json
import logging
import threading
import time
from pathlib import Path
from typing import Any, Protocol

import httpx

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


class ChatModel(Protocol):
    def chat_json(self, model: str, messages: list[dict[str, str]], **kw: Any) -> dict: ...


class GroqClient:
    def __init__(
        self,
        api_key: str | None,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: float = 60.0,
        cache_path: Path | None = None,
        max_retries: int = 6,
    ) -> None:
        self.api_key, self.base_url = api_key, base_url.rstrip("/")
        self.http = httpx.Client(timeout=timeout)
        self.max_retries = max_retries
        self.cache_path = cache_path
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
        key = self._key(model, messages, kw)
        if key in self._cache:
            return self._cache[key]
        if not self.api_key:
            raise LLMError("GROQ_API_KEY is not set")
        body = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "max_completion_tokens": max_tokens,
            "response_format": {"type": "json_object"},
            "reasoning_effort": reasoning_effort,
            "include_reasoning": False,
        }
        output = self._post(body)
        with self._lock:
            self._cache[key] = output
            if self.cache_path:
                self.cache_path.parent.mkdir(parents=True, exist_ok=True)
                with self.cache_path.open("a", encoding="utf-8") as fh:
                    fh.write(json.dumps({"key": key, "output": output}, ensure_ascii=False) + "\n")
        return output

    def _post(self, body: dict) -> dict:
        delay = 2.0
        for attempt in range(1, self.max_retries + 1):
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
                    content = r.json()["choices"][0]["message"].get("content") or ""
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError:
                        err = f"model returned invalid JSON: {content[:200]!r}"
                elif r.status_code in (429, 500, 502, 503, 504) or (
                    r.status_code == 400 and "json_validate_failed" in r.text
                ):
                    err = f"HTTP {r.status_code}: {r.text[:200]}"
                    retry_after = r.headers.get("retry-after")
                    if retry_after:
                        delay = max(delay, float(retry_after))
                else:
                    raise LLMError(f"HTTP {r.status_code}: {r.text[:300]}")
            if attempt == self.max_retries:
                raise LLMError(err)
            log.warning("Groq call failed (%s), retry %d in %.0fs", err, attempt, delay)
            time.sleep(delay)
            delay = min(delay * 2, 60)
        raise LLMError("unreachable")
