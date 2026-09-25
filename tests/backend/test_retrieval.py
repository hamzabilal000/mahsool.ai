import hashlib
from datetime import date

import pytest

from backend.app.config import Settings
from backend.app.rag.bm25 import BM25, tokenize
from backend.app.rag.embedder import Encoded
from backend.app.rag.fusion import rrf
from backend.app.rag.retriever import Retriever
from backend.app.rag.store import VectorStore, make_client, point_id
from eval.metrics import hit_at_k, recall_at_k, reciprocal_rank
from ingestion.models import Chunk


def chunk(cid: str, text: str, section: str | None = None, **kw) -> Chunk:
    return Chunk(
        chunk_id=cid,
        section_id=section or cid,
        snapshot_id="T@2026-06-30",
        law="Test",
        law_code="TST",
        kind="section",
        title=cid,
        text=text,
        tax_year_from=kw.get("ty", 2027),
        tax_year_to=kw.get("ty_to"),
        source_url="https://x",
        page=1,
        page_end=1,
        version_date=date(2026, 6, 30),
        n_tokens=10,
    )


class FakeEmbedder:
    """Deterministic bag-of-words vectors: enough to test the plumbing without a model."""

    dim = 64

    def encode(self, texts: list[str], *, is_query: bool = False) -> list[Encoded]:
        out = []
        for t in texts:
            dense = [0.0] * self.dim
            sparse: dict[int, float] = {}
            for tok in tokenize(t):
                h = int(hashlib.md5(tok.encode()).hexdigest(), 16)
                dense[h % self.dim] += 1.0
                sparse[h % 10_000] = sparse.get(h % 10_000, 0.0) + 1.0
            out.append(Encoded(dense=dense, sparse=sparse))
        return out


CORPUS = [
    chunk("s149", "Every employer paying salary shall deduct tax at the average rate"),
    chunk("s155", "Tax shall be deducted from the gross amount of rent of immovable property"),
    chunk("s236K", "Advance tax on purchase of immovable property at fair market value"),
    chunk("s2-1", "Definitions active taxpayers list", section="s2"),
    chunk("s2-2", "Definitions continued salary means", section="s2"),
]


def test_rrf_rewards_agreement_between_rankings() -> None:
    fused = rrf([["a", "b", "c"], ["b", "a", "d"]], k=60)
    assert [d for d, _ in fused[:2]] in (["a", "b"], ["b", "a"])
    assert dict(fused)["a"] == pytest.approx(1 / 61 + 1 / 62)
    assert fused[-1][0] in {"c", "d"}


def test_rrf_single_ranking_keeps_order() -> None:
    assert [d for d, _ in rrf([["x", "y", "z"]])] == ["x", "y", "z"]


def test_bm25_ranks_the_matching_section_first() -> None:
    bm = BM25([c.chunk_id for c in CORPUS], [c.text for c in CORPUS])
    assert bm.search("tax on rent of property")[0][0] == "s155"
    assert bm.search("کرایہ") == []  # Urdu words never match English text


def test_metrics_on_section_ids() -> None:
    retrieved = ["s2", "s2", "s149", "s155"]
    assert hit_at_k(retrieved, {"s155"}, k=3) == 1.0  # duplicates of s2 count once
    assert hit_at_k(retrieved, {"s155"}, k=2) == 0.0
    assert recall_at_k(retrieved, {"s149", "s236K"}, k=5) == 0.5
    assert reciprocal_rank(retrieved, {"s149"}) == 0.5


@pytest.fixture
def store() -> VectorStore:
    emb = FakeEmbedder()
    vs = VectorStore(make_client(Settings(), in_memory=True), "test", emb.dim)
    vs.recreate()
    vs.upsert(CORPUS, emb.encode([c.text for c in CORPUS]))
    return vs


@pytest.mark.parametrize("mode", ["dense", "sparse", "hybrid"])
def test_vector_retrieval_end_to_end(store: VectorStore, mode: str) -> None:
    r = Retriever(CORPUS, mode, store=store, embedder=FakeEmbedder(), candidates=5)
    hits = r.retrieve("deduct tax from rent of immovable property", k=3)
    assert hits[0].section_id == "s155"
    assert [h.rank for h in hits] == [1, 2, 3]


def test_multi_query_fusion(store: VectorStore) -> None:
    r = Retriever(CORPUS, "hybrid", store=store, embedder=FakeEmbedder(), candidates=5)
    hits = r.retrieve_many(["kiraya pe tax", "tax deducted from gross amount of rent"], k=2)
    assert hits[0].section_id == "s155"


def test_tax_year_filter_excludes_other_snapshots() -> None:
    emb = FakeEmbedder()
    old = chunk("old", "rent tax old rate", ty=2020, ty_to=2026)
    new = chunk("new", "rent tax new rate", ty=2027)
    vs = VectorStore(make_client(Settings(), in_memory=True), "ty", emb.dim)
    vs.recreate()
    vs.upsert([old, new], emb.encode([old.text, new.text]))
    r = Retriever([old, new], "dense", store=vs, embedder=emb, candidates=5, tax_year=2027)
    assert [h.chunk_id for h in r.retrieve("rent tax", k=5)] == ["new"]
    r.tax_year = 2025
    assert [h.chunk_id for h in r.retrieve("rent tax", k=5)] == ["old"]


def test_point_ids_differ_per_snapshot() -> None:
    a = chunk("s1", "x")
    b = a.model_copy(update={"version_date": date(2027, 6, 30)})
    assert point_id(a) != point_id(b)
