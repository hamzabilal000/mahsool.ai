"""Retrieval metrics computed on section ids (the citation unit), not chunk ids."""

from collections.abc import Sequence


def dedupe(section_ids: Sequence[str]) -> list[str]:
    """Several chunks of one section count once, in the order first retrieved."""
    seen: set[str] = set()
    return [s for s in section_ids if not (s in seen or seen.add(s))]


def hit_at_k(retrieved: Sequence[str], relevant: set[str], k: int) -> float:
    """1 if any relevant section is in the top k (the plan's Recall@5 for single-answer Qs)."""
    return float(any(s in relevant for s in dedupe(retrieved)[:k]))


def recall_at_k(retrieved: Sequence[str], gold: set[str], k: int) -> float:
    """Share of the gold sections found in the top k (stricter for multi-section questions)."""
    if not gold:
        return 0.0
    return len(gold & set(dedupe(retrieved)[:k])) / len(gold)


def reciprocal_rank(retrieved: Sequence[str], relevant: set[str], k: int = 10) -> float:
    for rank, s in enumerate(dedupe(retrieved)[:k], start=1):
        if s in relevant:
            return 1.0 / rank
    return 0.0
