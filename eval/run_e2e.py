"""End-to-end evaluation of /ask: refusals and citation accuracy per language group.

Runs the same AskService as the API (full pipeline + GPT OSS 120B answer + citation check) on
every question of a split, out-of-scope questions included. Metrics:

- in-scope questions: answered (not refused), and "correct citation": at least one cited
  section is a gold or acceptable section of the question;
- out-of-scope questions: refused.

Answer correctness against the reference answers is not scored here (it needs a judge; see
DECISIONS D35). LLM outputs are cached in eval/cache/groq.jsonl and reranker scores in
eval/cache/rerank.tsv, so a re-run replays them without Groq.

Questions whose answer call fails (e.g. Groq's free-tier daily token limit) are listed as
"not run" and left out of the metrics; re-running resumes from the cache.

Usage:
    python -m eval.run_e2e --split dev
    python -m eval.run_e2e --split test
"""

import argparse
import json
from collections import defaultdict
from datetime import date
from statistics import mean

from backend.app.config import get_settings
from backend.app.llm import LLMError
from eval.run_eval import LLM_CACHE, REPORT_GROUPS, REPORTS, RERANK_CACHE, report_group
from eval.validate_testset import load_testset


def build_service():
    from backend.app.rag.factory import build_pipeline, groq_client
    from backend.app.rag.generator import AnswerGenerator
    from backend.app.rag.pipeline import PipelineConfig
    from backend.app.service import AskService

    s = get_settings()
    llm = groq_client(s, cache_path=LLM_CACHE)
    pipeline = build_pipeline(
        PipelineConfig(candidates=s.rerank_candidates, rerank_query=s.rerank_query),
        settings=s,
        llm=llm,
        rerank_cache=RERANK_CACHE,
    )
    return AskService(
        pipeline,
        AnswerGenerator(llm, s.answer_model),
        answer_top_k=s.answer_top_k,
        refusal_threshold=s.refusal_threshold,
        last_tax_year=s.current_tax_year,
    )


def summarize(rows: list[dict]) -> dict:
    by: dict[str, list[dict]] = defaultdict(list)
    for r in rows:
        by[r["group"]].append(r)
        if r["group"] != "out_of_scope":
            by["in_scope"].append(r)
    summary = {}
    for g, rs in by.items():
        if g == "out_of_scope":
            summary[g] = {"n": len(rs), "refused": round(mean(r["refused"] for r in rs), 4)}
            continue
        answered = [r for r in rs if not r["refused"]]
        summary[g] = {
            "n": len(rs),
            "answered": round(len(answered) / len(rs), 4),
            # Share of all in-scope questions answered with a correct citation.
            "correct_citation": round(mean(r["citation_correct"] for r in rs), 4),
            # Same, among answered questions only.
            "correct_citation_answered": (
                round(mean(r["citation_correct"] for r in answered), 4) if answered else None
            ),
        }
    return summary


def to_markdown(name: str, split: str, summary: dict, rows: list[dict]) -> str:
    lines = [
        f"# End-to-end eval — {name} ({split} split, {date.today().isoformat()})",
        "",
        "| Group | n | Answered | Correct citation (all) | Correct citation (answered) |",
        "|---|---|---|---|---|",
    ]
    for g in [*REPORT_GROUPS, "in_scope"]:
        s = summary.get(g)
        if s:
            ca = s["correct_citation_answered"]
            lines.append(
                f"| {g} | {s['n']} | {s['answered']:.1%} | {s['correct_citation']:.1%} "
                f"| {'-' if ca is None else f'{ca:.1%}'} |"
            )
    oos = summary.get("out_of_scope")
    if oos:
        lines += ["", f"Out-of-scope refused: **{oos['refused']:.1%}** of {oos['n']}."]
    if summary.get("not_run"):
        lines += [
            "",
            f"Not run ({len(summary['not_run'])}, LLM unavailable, e.g. Groq's daily token "
            f"limit; re-run to resume from the cache): {', '.join(summary['not_run'])}",
        ]
    bad = [
        r
        for r in rows
        if (r["group"] == "out_of_scope") != r["refused"]
        or (r["group"] != "out_of_scope" and not r["refused"] and not r["citation_correct"])
    ]
    lines += [
        "",
        f"## Failures ({len(bad)})",
        "",
        "| id | refused (reason) | gold | cited |",
        "|---|---|---|---|",
    ]
    lines += [
        f"| {r['id']} | {r['refusal_reason'] or 'no'} | {', '.join(r['gold'])} "
        f"| {', '.join(r['cited'])} |"
        for r in bad
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split", default="test", choices=["dev", "test", "all"])
    ap.add_argument("--name", default=None)
    args = ap.parse_args()

    items = [i for i in load_testset() if args.split == "all" or i.split == args.split]
    service = build_service()
    rows, not_run = [], []
    for n, item in enumerate(items, start=1):
        try:
            data = service.ask(item.question)
        except LLMError as e:  # e.g. Groq's daily token limit; re-run later, the cache resumes
            not_run.append(item.id)
            print(f"{n}/{len(items)} {item.id} NOT RUN: {e}", flush=True)
            continue
        relevant = set(item.gold_section_ids) | set(item.acceptable_section_ids)
        cited = [c.section_id for c in data.citations]
        rows.append(
            {
                "id": item.id,
                "group": report_group(item),
                "refused": data.refused,
                "refusal_reason": data.refusal_reason,
                "gold": item.gold_section_ids,
                "cited": cited,
                "citation_correct": (not data.refused) and bool(relevant & set(cited)),
                "answer": data.answer,
                "search_queries": data.search_queries,
                "warnings": data.warnings,
                "timings_ms": data.timings_ms,
            }
        )
        print(f"{n}/{len(items)} {item.id} refused={data.refused} cited={cited}", flush=True)

    summary = summarize(rows)
    summary["not_run"] = not_run
    name = args.name or f"e2e-{args.split}"
    REPORTS.mkdir(exist_ok=True)
    stem = REPORTS / f"{date.today().isoformat()}-{name}"
    result = {"summary": summary, "rows": rows}
    stem.with_suffix(".json").write_text(json.dumps(result, indent=1, ensure_ascii=False))
    md = to_markdown(name, args.split, summary, rows)
    stem.with_suffix(".md").write_text(md, encoding="utf-8")
    print(md.split("## Failures")[0])
    service.pipeline.retriever.store.client.close()


if __name__ == "__main__":
    main()
