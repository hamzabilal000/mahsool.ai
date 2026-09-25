"""Retrieval strategies used by the API and by the ablation study.

bm25    keyword baseline, no model
dense   BGE-M3 dense vectors (meaning)
sparse  BGE-M3 sparse lexical weights (exact terms such as section numbers)
hybrid  dense + sparse fused with reciprocal rank fusion (RRF)
"""

from dataclasses import dataclass
from typing import Literal

from backend.app.rag.bm25 import BM25
from backend.app.rag.corpus import embedding_text
from backend.app.rag.embedder import Embedder
from backend.app.rag.fusion import rrf
from backend.app.rag.store import VectorStore
from ingestion.models import Chunk

Mode = Literal["bm25", "dense", "sparse", "hybrid"]


@dataclass
class Hit:
    chunk_id: str
    section_id: str
    score: float
    rank: int


class Retriever:
    def __init__(
        self,
        chunks: list[Chunk],
        mode: Mode,
        *,
        store: VectorStore | None = None,
        embedder: Embedder | None = None,
        candidates: int = 30,
        rrf_k: int = 60,
        tax_year: int | None = None,
    ) -> None:
        self.mode = mode
        self.by_id = {c.chunk_id: c for c in chunks}
        self.store, self.embedder = store, embedder
        self.candidates, self.rrf_k, self.tax_year = candidates, rrf_k, tax_year
        if mode == "bm25":
            self.bm25 = BM25([c.chunk_id for c in chunks], [embedding_text(c) for c in chunks])
        elif store is None or embedder is None:
            raise ValueError(f"mode {mode!r} needs a vector store and an embedder")

    def retrieve(self, query: str, k: int = 10) -> list[Hit]:
        return self.retrieve_many([query], k)

    def retrieve_many(
        self, queries: list[str], k: int = 10, *, tax_year: int | None = None
    ) -> list[Hit]:
        """Search with one or more phrasings of the question and fuse the rankings with RRF.

        `tax_year` overrides the retriever's default tax-year filter for this call.
        """
        rankings: list[list[str]] = []
        if self.mode == "bm25":
            rankings = [[cid for cid, _ in self.bm25.search(q, self.candidates)] for q in queries]
        else:
            assert self.store is not None and self.embedder is not None
            flt = VectorStore.tax_year_filter(tax_year or self.tax_year)
            for enc in self.embedder.encode(queries, is_query=True):
                if self.mode in ("dense", "hybrid"):
                    rankings.append(
                        [c for c, _ in self.store.search_dense(enc.dense, self.candidates, flt)]
                    )
                if self.mode in ("sparse", "hybrid"):
                    rankings.append(
                        [c for c, _ in self.store.search_sparse(enc.sparse, self.candidates, flt)]
                    )
        fused = rankings[0] if len(rankings) == 1 else [c for c, _ in rrf(rankings, self.rrf_k)]
        scores = dict(rrf(rankings, self.rrf_k))
        return [
            Hit(chunk_id=cid, section_id=self.by_id[cid].section_id, score=scores[cid], rank=i)
            for i, cid in enumerate(fused[:k], start=1)
        ]
