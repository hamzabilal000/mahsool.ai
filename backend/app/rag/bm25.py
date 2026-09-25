"""Okapi BM25 over chunk text — a no-model keyword baseline for the ablation table.

It matches exact words only, so it shows how far plain keyword search gets on English
questions, and how badly it fails when the question is in Urdu script or Roman Urdu.
"""

import math
import re
from collections import Counter
from collections.abc import Sequence

TOKEN_RE = re.compile(r"\w+", re.UNICODE)
STOPWORDS = frozenset(
    {
        "a",
        "an",
        "and",
        "are",
        "as",
        "at",
        "be",
        "by",
        "for",
        "from",
        "has",
        "have",
        "if",
        "in",
        "is",
        "it",
        "its",
        "of",
        "on",
        "or",
        "shall",
        "that",
        "the",
        "this",
        "to",
        "under",
        "was",
        "were",
        "which",
        "with",
        "any",
        "such",
    }
)


def tokenize(text: str) -> list[str]:
    return [t for t in (m.group().lower() for m in TOKEN_RE.finditer(text)) if t not in STOPWORDS]


class BM25:
    def __init__(self, ids: Sequence[str], texts: Sequence[str], k1: float = 1.5, b: float = 0.75):
        self.ids = list(ids)
        self.k1, self.b = k1, b
        self.docs = [Counter(tokenize(t)) for t in texts]
        self.lengths = [sum(d.values()) for d in self.docs]
        self.avgdl = sum(self.lengths) / max(len(self.docs), 1)
        df: Counter[str] = Counter()
        for d in self.docs:
            df.update(d.keys())
        n = len(self.docs)
        self.idf = {term: math.log(1 + (n - f + 0.5) / (f + 0.5)) for term, f in df.items()}

    def search(self, query: str, k: int = 10) -> list[tuple[str, float]]:
        terms = [t for t in tokenize(query) if t in self.idf]
        scores = []
        for i, doc in enumerate(self.docs):
            s = 0.0
            norm = self.k1 * (1 - self.b + self.b * self.lengths[i] / self.avgdl)
            for t in terms:
                tf = doc.get(t, 0)
                if tf:
                    s += self.idf[t] * tf * (self.k1 + 1) / (tf + norm)
            if s > 0:
                scores.append((self.ids[i], s))
        scores.sort(key=lambda x: -x[1])
        return scores[:k]
