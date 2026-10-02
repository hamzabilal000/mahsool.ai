"""The retrieval pipeline used by /ask and by the ablation study.

    question
      -> query understanding (language, tax year, English rewrites)        query_rewrite.py
      -> hybrid search for the original + each rewrite, fused with RRF     retriever.py
      -> sections named in the question ("section 149") pinned on top      lookup.py
      -> sections the glossary names for the user's words added to the pool (D69)
      -> top 30 reranked by a cross-encoder                                reranker.py
      -> companions: the Tenth Schedule rule a rate depends on (ATL, D63)   lookup.py

Each step can be switched off, which is how the ablation table is produced.
"""

import math
import re
from collections import Counter
from dataclasses import dataclass, field
from typing import Literal

from backend.app.rag.corpus import embedding_text
from backend.app.rag.lookup import AtlRuleLookup, DefinitionLookup, SectionLookup
from backend.app.rag.query_rewrite import QueryPlan, QueryRewriter
from backend.app.rag.reranker import Reranker, score_many
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
    definitions: bool = True  # pin the section 2 clause for "what is X?" questions (D57)
    # Add the sections the glossary names for the user's words ("pension" -> section 149; rows
    # marked "search") to the reranker's pool, not on top: the reranker decides whether they
    # fit (D69). At most this many sections, longest glossary matches first.
    glossary_sections: int = 6
    # "max": score each chunk against the question and the first English rewrite, keep the
    # higher score (DECISIONS D33). Doubles the reranker cost. "max_non_en": the same, but only
    # for Urdu / Roman Urdu questions, where it helps (D40, D52); English questions are scored once.
    rerank_query: Literal["original", "max", "max_non_en"] = "original"
    # The reranker reads ~256 tokens, so the end of a long chunk (section 149(1A) on pension,
    # 12(7) on salary arrears) is never seen. For chunks longer than `window_chars`, also score
    # the chunk header + the window that shares the rarest words with the question and its
    # rewrites, and keep the higher score (D69). 0 = off.
    window_chars: int = 800
    # Add the Tenth Schedule rule (and, for filer questions, the rate card) that the answer
    # sources' rates depend on, after the ranked sources (D63).
    atl_rules: bool = True


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


_WORD = re.compile(r"[a-z]{4,}")


def _windows(text: str, size: int) -> list[tuple[int, str]]:
    """Overlapping windows of about `size` characters after the first one, starting at a word."""
    out, start, step = [], size * 3 // 4, size * 3 // 4
    while start < len(text) - size // 4:
        begin = text.find(" ", start) + 1 or start
        out.append((begin, text[begin : begin + size]))
        start += step
    return out


def _in_year(chunk: Chunk, tax_year: int) -> bool:
    return tax_year >= chunk.tax_year_from and (
        chunk.tax_year_to is None or tax_year <= chunk.tax_year_to
    )


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
        self.definitions = DefinitionLookup(chunks)
        self.atl = AtlRuleLookup(chunks)
        self.config = config or PipelineConfig()
        # Document frequency of each word, to weigh rare words when choosing a window.
        df = Counter(w for c in chunks for w in set(_WORD.findall(c.text.lower())))
        self._idf = {w: math.log(len(chunks) / n) for w, n in df.items()}
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
            # "What is imputable income?": the section 2 clause that defines the term (D57). The
            # English rewrites are checked too, so Urdu / Roman Urdu questions benefit.
            texts = [question, *plan.queries]
            asked = [f[2] for f in self.definitions.find(texts)] if cfg.definitions else []
            # A definition that only points elsewhere ("as defined in section 9") pins that section.
            for sid in self.definitions.targets(texts) if cfg.definitions else []:
                ids = sorted(self.lookup.chunk_ids(sid), key=lambda cid: order.get(cid, len(order)))
                asked += ids[: cfg.max_pieces_per_lookup]
            for cid in asked:
                chunk = self.by_id[cid]
                if cid not in {c.chunk_id for c in pinned} and plan.tax_year >= chunk.tax_year_from:
                    pinned.append(Candidate(chunk, rank=0, via="lookup"))
            pinned_ids = {c.chunk_id for c in pinned}
            found = [c for c in found if c.chunk_id not in pinned_ids]

        if cfg.glossary_sections and plan.glossary_sections:
            have = {c.chunk_id for c in pinned + found}
            order = {c.chunk_id: i for i, c in enumerate(found)}
            for sid in plan.glossary_sections[: cfg.glossary_sections]:
                ids = sorted(self.lookup.chunk_ids(sid), key=lambda cid: order.get(cid, len(order)))
                for cid in ids[: cfg.max_pieces_per_lookup]:
                    chunk = self.by_id[cid]
                    if cid not in have and _in_year(chunk, plan.tax_year):
                        found.append(Candidate(chunk, rank=len(found) + 1))
                        have.add(cid)

        if cfg.rerank and self.reranker is not None:
            pool = pinned + found
            texts = [embedding_text(c.chunk) for c in pool]
            owner = list(range(len(pool)))  # passage -> pool index
            if cfg.window_chars:
                words = set(_WORD.findall(" ".join([question, *plan.queries]).lower()))
                for i, c in enumerate(pool):
                    window = self._best_window(c.chunk, words, cfg.window_chars)
                    if window:
                        texts.append(window)
                        owner.append(i)
            with stage("rerank"):
                use_max = cfg.rerank_query == "max" or (
                    cfg.rerank_query == "max_non_en" and plan.language != "en"
                )
                queries = [question, plan.queries[0]] if use_max and plan.queries else [question]
                per_query = score_many(self.reranker, queries, texts)
                passage_scores = [max(col) for col in zip(*per_query, strict=True)]
                # Sections the glossary names for the user's words are also scored against
                # every English rewrite, which states that meaning in the law's words (D69).
                named = set(plan.glossary_sections) if cfg.glossary_sections else set()
                extra = [j for j, i in enumerate(owner) if pool[i].section_id in named]
                rewrites = [q for q in plan.queries if q not in queries]
                if extra and rewrites:
                    more = score_many(self.reranker, rewrites, [texts[j] for j in extra])
                    for j, col in zip(extra, zip(*more, strict=True), strict=True):
                        passage_scores[j] = max(passage_scores[j], *col)
            scores = [0.0] * len(pool)
            for i, s in zip(owner, passage_scores, strict=True):
                scores[i] = max(scores[i], s)
            for c, s in zip(pool, scores, strict=True):
                c.rerank_score = s
            pinned.sort(key=lambda c: -(c.rerank_score or 0.0))
            found.sort(key=lambda c: -(c.rerank_score or 0.0))

        ranked = pinned + found
        for i, c in enumerate(ranked, start=1):
            c.rank = i
        return SearchResult(plan=plan, candidates=ranked, missing_refs=missing)

    def _best_window(self, chunk: Chunk, words: set[str], size: int) -> str | None:
        """Header + the later window of a long chunk with the most rare question words, or None
        when the chunk is short or no later window shares a word with the question."""
        if len(chunk.text) <= size:
            return None
        best, best_score = None, 0.0
        for _, text in _windows(chunk.text, size):
            score = sum(self._idf.get(w, 0.0) for w in words & set(_WORD.findall(text.lower())))
            if score > best_score:
                best, best_score = text, score
        if best is None:
            return None
        head = embedding_text(chunk).split("\n", 1)[0]
        return f"{head}\n... {best}"

    def companions(self, result: SearchResult, top_k: int) -> list[Chunk]:
        """Extra answer sources for the top `top_k` candidates: the Tenth Schedule rule their
        ATL / non-ATL rates depend on, and for a filer question the rate card (D63)."""
        if not self.config.atl_rules:
            return []
        top = [c.chunk for c in result.candidates[:top_k]]
        texts = [result.plan.question, *result.plan.queries]
        named = result.plan.glossary_named
        return [self.by_id[cid] for cid in self.atl.companions(top, texts, named=named)]
