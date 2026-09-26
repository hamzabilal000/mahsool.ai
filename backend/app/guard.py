"""Prompt Guard: screen questions for prompt injection and jailbreak attempts (PROJECT_PLAN
guardrails, D60).

Meta's Llama Prompt Guard 2 (86M) is a small classifier that Groq serves on its free tier; it
returns one number, the probability that the text is an attack ("ignore all previous
instructions and ..."). It reads English, Urdu and Roman Urdu (multilingual mDeBERTa base).
A question at or above the threshold is refused before any search or answer model runs.

The check fails open: if Groq is unreachable or the quota is used up, the question goes on to the
normal pipeline, whose own guardrails (scope check, grounded answer, citation check) still hold.
An outage of a safety add-on should not take the whole demo down.
"""

import logging

import httpx

log = logging.getLogger(__name__)


class PromptGuard:
    def __init__(
        self,
        api_key: str,
        model: str = "meta-llama/llama-prompt-guard-2-86m",
        threshold: float = 0.5,
        base_url: str = "https://api.groq.com/openai/v1",
        timeout: float = 5.0,
    ) -> None:
        self.model, self.threshold = model, threshold
        self.url = f"{base_url.rstrip('/')}/chat/completions"
        self.headers = {"Authorization": f"Bearer {api_key}"}
        self.http = httpx.Client(timeout=timeout)

    def score(self, text: str) -> float | None:
        """Probability that `text` is an attack, or None if the check could not run."""
        body = {"model": self.model, "messages": [{"role": "user", "content": text}]}
        try:
            r = self.http.post(self.url, headers=self.headers, json=body)
            r.raise_for_status()
            return float(r.json()["choices"][0]["message"]["content"].strip())
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as e:
            log.warning("prompt guard unavailable, letting the question through: %s", e)
            return None

    def flags(self, text: str) -> bool:
        s = self.score(text)
        return s is not None and s >= self.threshold
