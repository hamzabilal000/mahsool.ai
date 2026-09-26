"""Tune the reranker's workload on the dev split: rerank candidates x "max" policy (D52).

Hit@5 comes from the committed reranker score cache (eval/cache/rerank.tsv; a missing pair is
scored and cached), and rewrites from eval/cache/groq.jsonl with no API key, so the sweep costs
no quota. Rerank time is proportional to the number of (query, chunk) pairs scored, so the sweep
reports pairs per question; multiply by the per-pair cost measured with eval/latency.py.

Usage:
    python -m eval.rerank_sweep --split dev
"""

import argparse
import json
from datetime import date
from statistics import mean

from backend.app.config import get_settings
from backend.app.rag.pipeline import PipelineConfig
from eval.run_eval import LLM_CACHE, REPORTS, RERANK_CACHE, PipelineAdapter, evaluate
from eval.validate_testset import load_testset


class CountingReranker:
    def __init__(self, inner) -> None:
        self.inner, self.pairs = inner, 0

    def score(self, query: str, passages: list[str]) -> list[float]:
        self.pairs += len(passages)
        return self.inner.score(query, passages)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--candidates", default="10,15,20,30")
    args = ap.parse_args()

    from backend.app.rag.factory import LLMClients, build_pipeline

    s = get_settings().model_copy(update={"groq_api_key": None, "gemini_api_key": None})
    llm = LLMClients(s, cache_path=LLM_CACHE)
    items = [i for i in load_testset() if i.split == args.split and i.group != "out_of_scope"]
    results = []
    for policy in ("original", "max_non_en", "max"):
        for n in [int(x) for x in args.candidates.split(",")]:
            config = PipelineConfig(candidates=n, rerank_query=policy)
            pipeline = build_pipeline(config, settings=s, llm=llm, rerank_cache=RERANK_CACHE)
            counter = CountingReranker(pipeline.reranker)
            pipeline.reranker = counter
            summary = evaluate(items, PipelineAdapter(pipeline), k=5)["summary"]
            row = {"rerank_query": policy, "candidates": n,
                   "pairs_per_question": round(counter.pairs / len(items), 1),
                   "hit@5": {g: v["hit@5"] for g, v in summary.items()},
                   "mrr@10_all": summary["all"]["mrr@10"]}  # fmt: skip
            results.append(row)
            print(json.dumps(row), flush=True)
    out = REPORTS / f"{date.today().isoformat()}-rerank-sweep-{args.split}.json"
    out.write_text(json.dumps(results, indent=1), encoding="utf-8")
    best = max(results, key=lambda r: (r["hit@5"]["all"], -r["pairs_per_question"]))
    pairs = mean(r["pairs_per_question"] for r in results)
    print(f"best Hit@5 on {args.split}: {best} (mean pairs {pairs:.0f})")


if __name__ == "__main__":
    main()
