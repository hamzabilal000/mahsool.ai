"""Where does the time go? Per-stage latency of the retrieval pipeline, and its Hit@5, on a split.

Runs the real models (BGE-M3, the reranker: no score cache, so rerank time is real compute) on
every question of the split. The rewrite step replays eval/cache/groq.jsonl only: no API key
is used, so this costs no quota and a question whose rewrite is not cached is skipped. The answer
LLM is not called; its time is taken from the end-to-end reports (see --e2e), where it includes
Groq rate-limit waits.

Usage (tune on dev only, D52):
    python -m eval.latency --split dev --name baseline
    python -m eval.latency --split dev --name c15 --candidates 15
    python -m eval.latency --split dev --name int8 --quantize
    python -m eval.latency --split dev --name maxnonen --rerank-query max_non_en
    python -m eval.latency --split dev --name gte --candidates 15 --rerank-query max_non_en \
        --reranker-model Alibaba-NLP/gte-multilingual-reranker-base --threads 2
"""

import argparse
import json
import time
from datetime import date
from statistics import median

from backend.app.config import get_settings
from backend.app.llm import LLMError
from backend.app.rag.pipeline import PipelineConfig, RAGPipeline
from backend.app.timing import request_timer
from eval.metrics import hit_at_k
from eval.run_eval import LLM_CACHE, REPORTS, report_group
from eval.validate_testset import load_testset

STAGES = ["rewrite", "retrieval", "rerank", "llm_wait", "llm_api", "total"]


def pct(values: list[float], q: float) -> float:
    if not values:
        return 0.0
    s = sorted(values)
    return s[min(len(s) - 1, round(q * (len(s) - 1)))]


def build(
    candidates: int, rerank_query: str, quantize: bool, model: str | None = None,
    max_length: int | None = None,
) -> tuple[RAGPipeline, float]:  # fmt: skip
    from backend.app.rag import factory
    from backend.app.rag.query_rewrite import Glossary, QueryRewriter
    from backend.app.rag.reranker import make_reranker
    from backend.app.rag.retriever import Retriever

    update = {"groq_api_key": None, "gemini_api_key": None, "reranker_quantize": quantize}
    if model:
        update["reranker_model"] = model
    if max_length:
        update["reranker_max_length"] = max_length
    s = get_settings().model_copy(update=update)
    t = time.perf_counter()
    retriever = Retriever(
        factory.chunks(), "hybrid", store=factory.store(), embedder=factory.embedder(),
        candidates=s.candidates_per_retriever, rrf_k=s.rrf_k, tax_year=s.current_tax_year,
    )  # fmt: skip
    reranker = make_reranker(s)
    load_s = time.perf_counter() - t
    llm, model = factory.LLMClients(s, cache_path=LLM_CACHE).for_role("rewrite")
    rewriter = QueryRewriter(llm, model, Glossary.load(s.glossary_path),
                             current_tax_year=s.current_tax_year)  # fmt: skip
    config = PipelineConfig(candidates=candidates, rerank_query=rerank_query)
    return RAGPipeline(factory.chunks(), retriever, rewriter, reranker, config), load_s


def e2e_answer_times() -> dict:
    """Answer-step times from end-to-end reports (they include rate-limit waits)."""
    times = []
    for path in sorted(REPORTS.glob("*-e2e-*.json")):
        for row in json.loads(path.read_text(encoding="utf-8"))["rows"]:
            t = row.get("timings_ms", {})
            if not row["refused"] and "answer" in t:
                times.append(t.get("answer_llm", t["answer"]) / 1000)
    return {"n": len(times), "p50_s": round(median(times), 2) if times else None,
            "p95_s": round(pct(times, 0.95), 2) if times else None}  # fmt: skip


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--name", required=True)
    ap.add_argument("--candidates", type=int, default=30)
    ap.add_argument("--rerank-query", default="max", choices=["original", "max", "max_non_en"])
    ap.add_argument("--quantize", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--reranker-model", help="default: settings.reranker_model")
    ap.add_argument("--max-length", type=int, help="reranker max tokens per pair")
    ap.add_argument("--threads", type=int, help="PyTorch CPU threads (the free Space has 2)")
    args = ap.parse_args()

    if args.threads:
        import torch

        torch.set_num_threads(args.threads)
    pipeline, load_s = build(args.candidates, args.rerank_query, args.quantize,
                             args.reranker_model, args.max_length)  # fmt: skip
    items = [i for i in load_testset() if i.split == args.split and i.group != "out_of_scope"]
    if args.limit:
        items = items[: args.limit]
    for item in items:  # warm-up on a question whose rewrite is cached; not measured
        try:
            pipeline.search(item.question)
            break
        except LLMError:
            continue

    rows, skipped = [], []
    for n, item in enumerate(items, start=1):
        with request_timer() as timer:
            try:
                result = pipeline.search(item.question)
            except LLMError:  # rewrite not cached; no API calls are made here
                skipped.append(item.id)
                continue
        t = timer.result()
        top = [c.section_id for c in result.candidates]
        gold = set(item.gold_section_ids) | set(item.acceptable_section_ids)
        rows.append({"id": item.id, "group": report_group(item), "language": item.language,
                     "hit@5": hit_at_k(top, gold, 5), "ms": t})  # fmt: skip
        print(f"{n}/{len(items)} {item.id} {t.get('total', 0)} ms", flush=True)

    summary = {"stages_s": {}, "load_s": round(load_s, 1)}
    for st in STAGES:
        vals = [r["ms"].get(st, 0) / 1000 for r in rows]
        summary["stages_s"][st] = {"p50": round(median(vals), 2) if vals else None,
                                   "p95": round(pct(vals, 0.95), 2)}  # fmt: skip
    groups = sorted({r["group"] for r in rows})
    summary["hit@5"] = {g: round(sum(r["hit@5"] for r in rows if r["group"] == g)
                                 / max(1, sum(r["group"] == g for r in rows)), 4)
                        for g in groups}  # fmt: skip
    summary["hit@5"]["all"] = round(sum(r["hit@5"] for r in rows) / max(1, len(rows)), 4)
    summary["n"], summary["skipped"] = len(rows), skipped
    summary["answer_llm_from_e2e"] = e2e_answer_times()
    summary["config"] = {"candidates": args.candidates, "rerank_query": args.rerank_query,
                         "quantize": args.quantize, "split": args.split,
                         "reranker_model": args.reranker_model or get_settings().reranker_model,
                         "max_length": args.max_length or get_settings().reranker_max_length,
                         "threads": args.threads}  # fmt: skip

    REPORTS.mkdir(exist_ok=True)
    out = REPORTS / f"{date.today().isoformat()}-latency-{args.name}-{args.split}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1), encoding="utf-8")
    print(json.dumps(summary, indent=1))
    pipeline.retriever.store.client.close()


if __name__ == "__main__":
    main()
