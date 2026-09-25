"""Reciprocal Rank Fusion (RRF): merge several ranked lists into one.

score(doc) = sum over lists of 1 / (k + rank), rank starting at 1. A document ranked highly
by any retriever gets a good score, and one ranked well by several gets a better one. Only
ranks are used, so the raw scores of dense (cosine) and sparse (dot product) search never
have to be put on the same scale. k = 60 is the value from the original paper
(Cormack et al., 2009); it damps the difference between rank 1 and rank 2.
"""

from collections import defaultdict
from collections.abc import Sequence


def rrf(rankings: Sequence[Sequence[str]], k: int = 60) -> list[tuple[str, float]]:
    scores: dict[str, float] = defaultdict(float)
    first_seen: dict[str, int] = {}
    for ranking in rankings:
        for rank, doc_id in enumerate(ranking, start=1):
            scores[doc_id] += 1.0 / (k + rank)
            first_seen.setdefault(doc_id, len(first_seen))
    # Ties broken by first appearance, so the result is deterministic.
    return sorted(scores.items(), key=lambda kv: (-kv[1], first_seen[kv[0]]))
