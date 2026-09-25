"""Cross-encoder reranking with bge-reranker-v2-m3.

Retrieval embeds the question and each chunk *separately* and compares vectors, which is fast
but coarse. A cross-encoder reads the question and one chunk *together* and outputs a single
relevance score, which is far more precise but too slow to run on the whole corpus. So we
retrieve ~30 candidates cheaply, then rerank only those.
"""

import hashlib
from pathlib import Path
from typing import Protocol

from backend.app.config import Settings


class Reranker(Protocol):
    def score(self, query: str, passages: list[str]) -> list[float]: ...


class BGEReranker:
    """BAAI/bge-reranker-v2-m3 through FlagEmbedding. Scores are sigmoid-normalised to 0..1."""

    def __init__(self, settings: Settings) -> None:
        from FlagEmbedding import FlagReranker

        self.max_length = settings.reranker_max_length
        self.batch_size = settings.reranker_batch_size
        self.model = FlagReranker(
            settings.reranker_model,
            use_fp16=False,  # CPU
            cache_dir=str(settings.hf_cache_dir) if settings.hf_cache_dir else None,
        )

    def score(self, query: str, passages: list[str]) -> list[float]:
        if not passages:
            return []
        scores = self.model.compute_score(
            [[query, p] for p in passages],
            batch_size=self.batch_size,
            max_length=self.max_length,
            normalize=True,
        )
        return [float(s) for s in (scores if isinstance(scores, list) else [scores])]


class CachedReranker:
    """Wraps a reranker with an on-disk score cache keyed by (query, passage).

    Used by the ablation runs: several presets rerank the same question/chunk pairs, and on a
    CPU each pair costs ~0.5 s. The cache is a local speed-up only (gitignored).
    """

    def __init__(self, inner: Reranker, path: Path) -> None:
        self.inner, self.path = inner, path
        self.cache: dict[str, float] = {}
        if path.exists():
            for line in path.read_text(encoding="utf-8").splitlines():
                key, value = line.split("\t")
                self.cache[key] = float(value)

    @staticmethod
    def _key(query: str, passage: str) -> str:
        return hashlib.sha256(f"{query}\x00{passage}".encode()).hexdigest()[:24]

    def score(self, query: str, passages: list[str]) -> list[float]:
        keys = [self._key(query, p) for p in passages]
        todo = [i for i, k in enumerate(keys) if k not in self.cache]
        if todo:
            new = self.inner.score(query, [passages[i] for i in todo])
            self.path.parent.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                for i, s in zip(todo, new, strict=True):
                    self.cache[keys[i]] = s
                    fh.write(f"{keys[i]}\t{s}\n")
        return [self.cache[k] for k in keys]
