"""LLM client: providers, model fallback, rate limiter, cache and per-role settings (no network)."""

import json

import httpx
import pytest

from backend.app.config import Settings, role_model
from backend.app.llm import GEMINI, LLMClient, LLMError, RateLimiter
from backend.app.rag.factory import LLMClients


def ok(content: dict) -> httpx.Response:
    return httpx.Response(200, json={"choices": [{"message": {"content": json.dumps(content)}}]})


def client_with(handler, provider=GEMINI, **kw) -> LLMClient:
    client = LLMClient("key", provider, limiter=RateLimiter(None), **kw)
    client.http = httpx.Client(transport=httpx.MockTransport(handler))
    return client


def test_gemini_falls_back_when_model_is_not_served_and_caches_under_the_real_model(tmp_path):
    seen = []

    def handler(request):
        body = json.loads(request.content)
        seen.append(body["model"])
        assert "max_tokens" in body and "include_reasoning" not in body  # Gemini's fields
        if body["model"] == "gemini-3-flash":
            return httpx.Response(404, text='{"error": {"status": "NOT_FOUND"}}')
        return ok({"answer": "yes"})

    cache = tmp_path / "c.jsonl"
    fallbacks = {"gemini-3-flash": ["gemini-3-flash-preview", "gemini-2.5-flash"]}
    client = client_with(handler, cache_path=cache, fallbacks=fallbacks)
    msgs = [{"role": "user", "content": "q1"}]
    assert client.chat_json("gemini-3-flash", msgs) == {"answer": "yes"}
    assert client.resolved_model("gemini-3-flash") == "gemini-3-flash-preview"
    client.chat_json("gemini-3-flash", [{"role": "user", "content": "q2"}])
    assert seen == ["gemini-3-flash", "gemini-3-flash-preview", "gemini-3-flash-preview"]

    # A new process resumes from the cache without calling the API.
    again = client_with(lambda r: pytest.fail("no call expected"), cache_path=cache,
                        fallbacks=fallbacks)  # fmt: skip
    assert again.chat_json("gemini-3-flash", msgs) == {"answer": "yes"}


def test_gemini_daily_quota_fails_fast_and_fenced_json_is_parsed():
    calls = []

    def handler(request):
        calls.append(request)
        if len(calls) == 1:
            return ok_fenced()
        return httpx.Response(429, text='{"quotaId": "GenerateRequestsPerDayPerProjectPerModel"}')

    def ok_fenced():
        content = '```json\n{"a": 1}\n```'
        return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

    client = client_with(handler)
    assert client.chat_json("m", [{"role": "user", "content": "x"}]) == {"a": 1}
    with pytest.raises(LLMError, match="daily limit"):
        client.chat_json("m", [{"role": "user", "content": "y"}])
    assert len(calls) == 2


def test_rate_limiter_waits_for_the_minute_window_and_stops_at_the_daily_cap():
    now, slept = [0.0], []

    def sleep(s):
        slept.append(s)
        now[0] += s

    limiter = RateLimiter(2, per_day=3, clock=lambda: now[0], sleep=sleep)
    limiter.acquire()
    limiter.acquire()
    assert slept == []
    limiter.acquire()  # third request in the same minute waits ~60 s
    assert len(slept) == 1 and 59 < slept[0] < 61
    with pytest.raises(LLMError, match="daily limit"):
        limiter.acquire()


def test_roles_map_to_providers_and_share_one_client_per_provider():
    s = Settings(_env_file=None, groq_api_key="g", gemini_api_key="k")
    assert role_model(s, "judge1") == ("gemini", "gemini-3-flash")
    assert role_model(s, "judge2") == ("groq", "qwen/qwen3.8-27b")
    assert role_model(s, "answer") == ("groq", "openai/gpt-oss-120b")
    assert role_model(s, "rewrite") == ("groq", "openai/gpt-oss-20b")
    clients = LLMClients(s)
    answer, _ = clients.for_role("answer")
    rewrite, _ = clients.for_role("rewrite")
    judge1, _ = clients.for_role("judge1")
    assert answer is rewrite and judge1 is not answer
    assert judge1.spec.name == "gemini" and judge1.limiter.per_minute == 10
    assert judge1.limiter.per_day == 20


def test_after_a_daily_limit_the_model_is_not_called_again_but_cache_still_replays(tmp_path):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, text='{"error": {"message": "tokens per day (TPD)"}}')

    cache = tmp_path / "c.jsonl"
    cached_client = client_with(lambda r: ok({"a": 1}), cache_path=cache)
    cached_client.chat_json("m", [{"role": "user", "content": "cached"}])
    client = client_with(handler, cache_path=cache)
    for q in ("x", "y", "z"):
        with pytest.raises(LLMError, match="daily limit"):
            client.chat_json("m", [{"role": "user", "content": q}])
    assert len(calls) == 1  # one call, then the breaker
    assert client.chat_json("m", [{"role": "user", "content": "cached"}]) == {"a": 1}
