"""Retrieval evaluation: Recall@5 / full recall / MRR per language group.

Only in-scope questions are scored here (out-of-scope questions have no gold sections;
refusal accuracy is measured end-to-end in Milestone 3). Public numbers use --split test.

Usage:
    python -m eval.run_eval --retriever bm25 --split test
    python -m eval.run_eval --retriever hybrid --split dev --name hybrid-dev
    python -m eval.run_eval --pipeline full --split test      # Milestone 3 pipeline presets

Pipeline presets (each adds one step to hybrid search, for the ablation table):
    lookup          + direct section lookup ("section 149", "dafa 236K")
    rewrite         + English query rewrite (GPT OSS 20B), no glossary
    rewrite-rerank  + bge-reranker-v2-m3 on the top 30
    full            + Urdu glossary in the rewrite prompt (reranks with the question only)
    lookup-rerank   lookup + reranker without any LLM (runs without a Groq key)
    full-max        full, reranking with max(question, first rewrite) score (/ask default, D40)

LLM outputs are cached in eval/cache/groq.jsonl, so re-running replays them without Groq.
"""

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path
from statistics import mean

from backend.app.config import get_settings
from backend.app.rag.corpus import load_chunks
from backend.app.rag.retriever import Mode, Retriever
from eval.metrics import hit_at_k, recall_at_k, reciprocal_rank
from eval.schema import TestItem
from eval.validate_testset import load_testset

REPORTS = Path(__file__).resolve().parent / "reports"
LLM_CACHE = Path(__file__).resolve().parent / "cache" / "groq.jsonl"
RERANK_CACHE = Path(__file__).resolve().parent / "cache" / "rerank.tsv"
GROUPS = ["english", "urdu", "roman_urdu"]
# Reporting groups: FBR-sourced questions (English) are scored as their own group, so "english"
# stays the written English set and stays comparable across runs; "all" includes both.
REPORT_GROUPS = ["english", "fbr", "urdu", "roman_urdu"]


def report_group(item: TestItem) -> str:
    return "fbr" if item.source == "fbr" else item.group


PRESETS: dict[str, dict] = {
    "lookup": {"lookup": True, "rewrite": "none", "rerank": False},
    "lookup-rerank": {"lookup": True, "rewrite": "none", "rerank": True},
    "rewrite": {"lookup": True, "rewrite": "plain", "rerank": False},
    "rewrite-rerank": {"lookup": True, "rewrite": "plain", "rerank": True},
    "full": {"lookup": True, "rewrite": "glossary", "rerank": True},
    "full-max": {"lookup": True, "rewrite": "glossary", "rerank": True, "rerank_query": "max"},
}


class PipelineAdapter:
    """Gives a RAGPipeline the Retriever interface used by `evaluate`, and keeps the plan."""

    def __init__(self, pipeline) -> None:
        self.pipeline = pipeline
        self.last = None

    def retrieve(self, question: str, k: int = 20):
        self.last = self.pipeline.search(question)
        return self.last.candidates[:k]


def build_pipeline_retriever(preset: str) -> PipelineAdapter:
    from backend.app.rag.factory import LLMClients, build_pipeline
    from backend.app.rag.pipeline import PipelineConfig

    settings = get_settings()
    config = PipelineConfig(**PRESETS[preset], candidates=settings.rerank_candidates)
    llm = LLMClients(settings, cache_path=LLM_CACHE) if config.rewrite != "none" else None
    return PipelineAdapter(
        build_pipeline(config, settings=settings, llm=llm, rerank_cache=RERANK_CACHE)
    )


def build_retriever(mode: Mode) -> Retriever:
    settings = get_settings()
    chunks = load_chunks()
    if mode == "bm25":
        return Retriever(chunks, "bm25", candidates=settings.candidates_per_retriever)
    from backend.app.rag.embedder import BGEM3Embedder
    from backend.app.rag.store import VectorStore, make_client

    store = VectorStore(make_client(settings), settings.qdrant_collection, settings.embedding_dim)
    return Retriever(
        chunks,
        mode,
        store=store,
        embedder=BGEM3Embedder(settings),
        candidates=settings.candidates_per_retriever,
        rrf_k=settings.rrf_k,
        tax_year=settings.current_tax_year,
    )


def evaluate(items: list[TestItem], retriever: Retriever, k: int = 5) -> dict:
    per_group: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    rows = []
    for item in items:
        hits = retriever.retrieve(item.question, k=20)
        sections = [h.section_id for h in hits]
        extra = {}
        last = getattr(retriever, "last", None)
        if last is not None:
            extra = {
                "queries": last.plan.queries,
                "scope": last.plan.scope,
                "top_score": last.top_score,
                "missing_refs": last.missing_refs,
            }
        if item.group == "out_of_scope":
            rows.append({"id": item.id, "group": item.group, "top": sections[:k], **extra})
            continue
        relevant = set(item.gold_section_ids) | set(item.acceptable_section_ids)
        scores = {
            f"hit@{k}": hit_at_k(sections, relevant, k),
            f"recall@{k}": recall_at_k(sections, set(item.gold_section_ids), k),
            "mrr@10": reciprocal_rank(sections, relevant, 10),
        }
        for name, value in scores.items():
            per_group[report_group(item)][name].append(value)
            per_group["all"][name].append(value)
        rows.append(
            {
                "id": item.id,
                "group": report_group(item),
                "gold": item.gold_section_ids,
                "top": sections[:k],
                **scores,
                **extra,
            }
        )
    summary = {
        g: {m: round(mean(v), 4) for m, v in ms.items()} | {"n": len(ms[f"hit@{k}"])}
        for g, ms in per_group.items()
    }
    return {"summary": summary, "rows": rows}


def to_markdown(name: str, split: str, k: int, result: dict) -> str:
    lines = [
        f"# Retrieval eval — {name} ({split} split, {date.today().isoformat()})",
        "",
        f"| Group | n | Hit@{k} | Recall@{k} (all gold) | MRR@10 |",
        "|---|---|---|---|---|",
    ]
    for g in [*REPORT_GROUPS, "all"]:
        s = result["summary"].get(g)
        if s:
            lines.append(
                f"| {g} | {s['n']} | {s[f'hit@{k}']:.1%} | {s[f'recall@{k}']:.1%} "
                f"| {s['mrr@10']:.3f} |"
            )
    misses = [r for r in result["rows"] if r["group"] != "out_of_scope" and not r[f"hit@{k}"]]
    lines += [
        "",
        f"## Misses ({len(misses)})",
        "",
        "| id | gold | top-5 retrieved |",
        "|---|---|---|",
    ]
    lines += [f"| {r['id']} | {', '.join(r['gold'])} | {', '.join(r['top'])} |" for r in misses]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--retriever", default="bm25", choices=["bm25", "dense", "sparse", "hybrid"])
    ap.add_argument("--pipeline", choices=list(PRESETS), help="Milestone 3 pipeline preset")
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--name", default=None)
    args = ap.parse_args()

    items = [
        i
        for i in load_testset()
        # Pipeline runs also score out-of-scope questions (top reranker score, detected scope)
        # for refusal tuning; they never count in the retrieval metrics.
        if (i.group in GROUPS or args.pipeline) and (args.split == "all" or i.split == args.split)
    ]
    if args.pipeline:
        retriever = build_pipeline_retriever(args.pipeline)
        name = args.name or f"pipeline-{args.pipeline}-{args.split}"
    else:
        retriever = build_retriever(args.retriever)
        name = args.name or f"{args.retriever}-{args.split}"
    result = evaluate(items, retriever, k=args.k)
    REPORTS.mkdir(exist_ok=True)
    stem = REPORTS / f"{date.today().isoformat()}-{name}"
    stem.with_suffix(".json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    md = to_markdown(name, args.split, args.k, result)
    stem.with_suffix(".md").write_text(md, encoding="utf-8")
    print(md.split("## Misses")[0])
    store = getattr(getattr(retriever, "pipeline", retriever), "retriever", retriever).store
    if store is not None:
        store.client.close()  # embedded Qdrant: release the lock cleanly


if __name__ == "__main__":
    main()
