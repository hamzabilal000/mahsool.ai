"""The retrieval pipeline used by /ask and by the ablation study.

    question
      -> query understanding (language, tax year, English rewrites)        query_rewrite.py
      -> hybrid search for the original + each rewrite, fused with RRF     retriever.py
      -> sections named in the question ("section 149") pinned on top      lookup.py
      -> top 30 reranked by a cross-encoder                                reranker.py

Each step can be switched off, which is how the ablation table is produced.
"""

from dataclasses import dataclass, field
from typing import Literal

from backend.app.rag.corpus import embedding_text
from backend.app.rag.lookup import SectionLookup
from backend.app.rag.query_rewrite import QueryPlan, QueryRewriter
from backend.app.rag.reranker import Reranker
from backend.app.rag.retriever import Retriever
from backend.app.timing import stage
from ingestion.models import Chunk

RewriteMode = Literal["none", "plain", "glossary"]


@dataclass(frozen=True)
class PipelineConfig:
    lookup: bool = True
    rewrite: RewriteMode = "glossary"
    rerank: bool = True
    candidates: int = 30  # chunks passed to the reranker
    max_pieces_per_lookup: int = 3  # pieces of a named section pinned on top
    # "max": score each chunk against the question and the first English rewrite, keep the
    # higher score (DECISIONS D33). Doubles the reranker cost.
    rerank_query: Literal["original", "max"] = "original"


@dataclass
class Candidate:
    chunk: Chunk
    rank: int
    fused_score: float = 0.0
    rerank_score: float | None = None
    via: Literal["lookup", "search"] = "search"

    @property
    def chunk_id(self) -> str:
        return self.chunk.chunk_id

    @property
    def section_id(self) -> str:
        return self.chunk.section_id


@dataclass
class SearchResult:
    plan: QueryPlan
    candidates: list[Candidate]
    missing_refs: list[str] = field(default_factory=list)  # "section 999Z" (not in the law)

    @property
    def top_score(self) -> float | None:
        scores = [c.rerank_score for c in self.candidates if c.rerank_score is not None]
        return max(scores) if scores else None


class RAGPipeline:
    def __init__(
        self,
        chunks: list[Chunk],
        retriever: Retriever,
        rewriter: QueryRewriter,
        reranker: Reranker | None = None,
        config: PipelineConfig | None = None,
    ) -> None:
        self.by_id = {c.chunk_id: c for c in chunks}
        self.retriever, self.rewriter, self.reranker = retriever, rewriter, reranker
        self.lookup = SectionLookup(chunks)
        self.config = config or PipelineConfig()
        if self.config.rerank and reranker is None:
            raise ValueError("config.rerank needs a reranker")

    def search(self, question: str, *, tax_year: int | None = None) -> SearchResult:
        cfg = self.config
        with stage("rewrite"):
            plan = self.rewriter.plan(
                question, rewrite=cfg.rewrite != "none", use_glossary=cfg.rewrite == "glossary"
            )
        if tax_year is not None:
            plan.tax_year, plan.tax_year_assumed = tax_year, False

        with stage("retrieval"):
            hits = self.retriever.retrieve_many(
                [question, *plan.queries], k=cfg.candidates, tax_year=plan.tax_year
            )
        found = [Candidate(self.by_id[h.chunk_id], rank=h.rank, fused_score=h.score) for h in hits]

        pinned: list[Candidate] = []
        missing: list[str] = []
        if cfg.lookup:
            refs, missing = self.lookup.resolve(question)
            order = {c.chunk_id: i for i, c in enumerate(found)}
            for ref in refs:
                ids = self.lookup.chunk_ids(ref.section_id)
                # Pieces the search also found come first, in search order; then document order.
                ids.sort(key=lambda cid: order.get(cid, len(order)))
                for cid in ids[: cfg.max_pieces_per_lookup]:
                    chunk = self.by_id[cid]
                    if plan.tax_year >= chunk.tax_year_from and (
                        chunk.tax_year_to is None or plan.tax_year <= chunk.tax_year_to
                    ):
                        pinned.append(Candidate(chunk, rank=0, via="lookup"))
            pinned_ids = {c.chunk_id for c in pinned}
            found = [c for c in found if c.chunk_id not in pinned_ids]

        if cfg.rerank and self.reranker is not None:
            pool = pinned + found
            texts = [embedding_text(c.chunk) for c in pool]
            with stage("rerank"):
                scores = self.reranker.score(question, texts)
                if cfg.rerank_query == "max" and plan.queries:
                    alt = self.reranker.score(plan.queries[0], texts)
                    scores = [max(a, b) for a, b in zip(scores, alt, strict=True)]
            for c, s in zip(pool, scores, strict=True):
                c.rerank_score = s
            pinned.sort(key=lambda c: -(c.rerank_score or 0.0))
            found.sort(key=lambda c: -(c.rerank_score or 0.0))

        ranked = pinned + found
        for i, c in enumerate(ranked, start=1):
            c.rank = i
        return SearchResult(plan=plan, candidates=ranked, missing_refs=missing)
