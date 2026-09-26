"""Write eval/reports/summary.json: the latest scores for the public evaluation page.

Reads the latest report of each ablation setup, the latest end-to-end report and the test set
itself (verification state), so the page never shows a number that is not in a committed report.
The API serves the file at GET /eval/summary.

Usage:
    python -m eval.summary
"""

import json
from collections import Counter
from datetime import date
from pathlib import Path

from eval.run_eval import REPORT_GROUPS, REPORTS, report_group
from eval.validate_testset import load_testset

OUT = REPORTS / "summary.json"
EXPERT_SAMPLE = Path(__file__).resolve().parent / "expert_sample.json"
# (report name, label, short description) in ablation order; the last one is the /ask default.
SETUPS = [
    ("bm25-test", "BM25", "keyword search, no model"),
    ("sparse-test", "Sparse", "BGE-M3 sparse vectors"),
    ("dense-test", "Dense", "BGE-M3 dense vectors"),
    ("hybrid-test", "Hybrid", "dense + sparse, RRF (baseline)"),
    ("pipeline-lookup-test", "+ section lookup", "'section 149' goes straight to the section"),
    ("pipeline-lookup-rerank-test", "+ reranker", "bge-reranker-v2-m3 on the top 30, no rewrite"),
    ("pipeline-rewrite-test", "+ rewrite", "English query rewrite by an LLM, no reranker"),
    ("pipeline-rewrite-rerank-test", "+ rewrite + reranker", "both"),
    ("pipeline-full-test", "+ glossary", "Urdu glossary in the rewrite = full pipeline"),
    (
        "pipeline-full-max-test",
        "Full, max score",
        "reranker also scores the rewrite (/ask default)",
    ),
]


def latest(name: str) -> tuple[str, dict] | None:
    files = sorted(REPORTS.glob(f"????-??-??-{name}.json"))
    if not files:
        return None
    return files[-1].name[:10], json.loads(files[-1].read_text(encoding="utf-8"))


def pct(x: float | None) -> float | None:
    return None if x is None else round(100 * x, 1)


def build() -> dict:
    items = load_testset()
    test = [i for i in items if i.split == "test"]
    direct = [i for i in items if not i.source_id]
    opinions = Counter(i.second_opinion for i in direct if i.second_opinion)
    sample = json.loads(EXPERT_SAMPLE.read_text(encoding="utf-8")) if EXPERT_SAMPLE.exists() else {}
    review = sample.get("review", {})

    ablation = []
    for name, label, what in SETUPS:
        found = latest(name)
        if not found:
            continue
        run_date, report = found
        s = report["summary"]
        ablation.append(
            {
                "setup": label,
                "description": what,
                "date": run_date,
                "hit_at_5": {g: pct(s[g]["hit@5"]) for g in [*REPORT_GROUPS, "all"] if g in s},
                "recall_at_5_all": pct(s["all"]["recall@5"]),
                "mrr_at_10_all": round(s["all"]["mrr@10"], 3),
                "n": {g: s[g]["n"] for g in [*REPORT_GROUPS, "all"] if g in s},
            }
        )

    e2e = None
    found = latest("e2e-test")
    if found:
        run_date, report = found
        s = report["summary"]
        in_scope = s.get("in_scope", {})
        oos = s.get("out_of_scope", {})
        e2e = {
            "date": run_date,
            "questions": len(test),
            "run": len(test) - len(s.get("not_run", [])),
            "not_run": len(s.get("not_run", [])),
            "in_scope_run": in_scope.get("n", 0),
            "answered": pct(in_scope.get("answered")),
            "correct_citation": pct(in_scope.get("correct_citation")),
            "correct_citation_answered": pct(in_scope.get("correct_citation_answered")),
            "out_of_scope_run": oos.get("n", 0),
            "out_of_scope_refused": pct(oos.get("refused")),
            "by_group": {
                g: {
                    "n": s[g]["n"],
                    "correct_citation": pct(s[g]["correct_citation"]),
                }
                for g in REPORT_GROUPS
                if g in s
            },
        }

    return {
        "generated": date.today().isoformat(),
        "testset": {
            "questions": len(items),
            "test_split": len(test),
            "test_by_group": dict(Counter(report_group(i) for i in test)),
            # "reviewed" questions passed the machine checks too (D50), so they count in both.
            "machine_verified": sum(i.verified in ("machine", "reviewed") for i in items),
            "review_verified": sum(i.verified == "reviewed" for i in items),
            "human_verified": sum(i.verified == "human" for i in items),
            "not_verified_yet": sum(i.verified is False for i in items),
            "second_opinion_agreed": opinions["agree"],
            "second_opinion_checked": sum(opinions.values()),
            "directly_judged": len(direct),
            "review_sample": len(sample.get("questions", [])),
            # The sample review so far is by an AI tool; never label it a human or expert review.
            "review_by": review.get("reviewer"),
            "review_kind": review.get("kind"),
            "review_result": review.get("result"),
            "tax_professional_review": review.get("tax_professional_review", "pending"),
        },
        "retrieval_ablation": ablation,
        "end_to_end": e2e,
        "targets": [
            {"metric": "Retrieval Hit@5, Urdu and Roman Urdu", "target": "≥ 80%"},
            {"metric": "Answers with a correct citation", "target": "≥ 90%"},
            {"metric": "Correct refusal on out-of-scope questions", "target": "≥ 90%"},
            {"metric": "Answer correctness", "target": "≥ 85% (not scored yet)"},
        ],
    }


def main() -> None:
    OUT.write_text(json.dumps(build(), indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
