"""Retrieval evaluation: Recall@5 / full recall / MRR per language group.

Only in-scope questions are scored here (out-of-scope questions have no gold sections;
refusal accuracy is measured end-to-end in Milestone 3). Public numbers use --split test.

Usage:
    python -m eval.run_eval --retriever bm25 --split test
    python -m eval.run_eval --retriever hybrid --split dev --name hybrid-dev
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
GROUPS = ["english", "urdu", "roman_urdu"]


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
        relevant = set(item.gold_section_ids) | set(item.acceptable_section_ids)
        scores = {
            f"hit@{k}": hit_at_k(sections, relevant, k),
            f"recall@{k}": recall_at_k(sections, set(item.gold_section_ids), k),
            "mrr@10": reciprocal_rank(sections, relevant, 10),
        }
        for name, value in scores.items():
            per_group[item.group][name].append(value)
            per_group["all"][name].append(value)
        rows.append(
            {
                "id": item.id,
                "group": item.group,
                "gold": item.gold_section_ids,
                "top": sections[:k],
                **scores,
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
    for g in [*GROUPS, "all"]:
        s = result["summary"].get(g)
        if s:
            lines.append(
                f"| {g} | {s['n']} | {s[f'hit@{k}']:.1%} | {s[f'recall@{k}']:.1%} "
                f"| {s['mrr@10']:.3f} |"
            )
    misses = [r for r in result["rows"] if not r[f"hit@{k}"]]
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
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--k", type=int, default=5)
    ap.add_argument("--name", default=None)
    args = ap.parse_args()

    items = [
        i
        for i in load_testset()
        if i.group in GROUPS and (args.split == "all" or i.split == args.split)
    ]
    result = evaluate(items, build_retriever(args.retriever), k=args.k)
    name = args.name or f"{args.retriever}-{args.split}"
    REPORTS.mkdir(exist_ok=True)
    stem = REPORTS / f"{date.today().isoformat()}-{name}"
    stem.with_suffix(".json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    md = to_markdown(name, args.split, args.k, result)
    stem.with_suffix(".md").write_text(md, encoding="utf-8")
    print(md.split("## Misses")[0])


if __name__ == "__main__":
    main()
