"""Answer correctness: an LLM judge compares each end-to-end answer with the reference answer.

Reads the latest end-to-end report for a split (eval/run_e2e.py) and asks the required judge
(judge2, Qwen on Groq; D45) one question per answered in-scope question: does the app's answer
say the same thing as the reference answer? The judge sees the question, the reference answer
and the app's answer only (no law text, no model names), and answers "yes", "partly" or "no".

- correct (strict): "yes"; correct (lenient): "yes" or "partly".
- An in-scope question the app refused counts as not correct; out-of-scope questions are
  correct when refused (same as the end-to-end report).
- Questions not run end to end yet are listed and left out; re-run after run_e2e resumes.

Verdicts are cached in eval/cache/answer_judge.jsonl, so a run stopped by the daily limit
resumes where it stopped (the client stops calling the judge after the first daily-limit error).

Usage:
    python -m eval.judge_answers --split test
"""

import argparse
import json
from collections import defaultdict
from datetime import date
from pathlib import Path

from backend.app.config import get_settings
from backend.app.llm import LLMError
from backend.app.rag.factory import LLMClients
from eval.run_eval import REPORT_GROUPS, REPORTS
from eval.validate_testset import load_testset

CACHE = Path(__file__).resolve().parent / "cache" / "answer_judge.jsonl"

SYSTEM = """You compare two answers to a question about Pakistani income tax: a REFERENCE \
answer written from the law text, and an APP answer. Judge only whether the app answer says \
the same thing as the reference; do not use your own knowledge of tax law.

- "yes": the app answer gives the same answer as the reference (same rates, amounts, \
conditions and conclusion); extra correct detail or different wording is fine.
- "partly": the main answer matches but a condition, exception, number or part of the \
reference is missing or different.
- "no": the app answer contradicts the reference, gives a different rate or conclusion, or \
does not answer the question.

Return JSON only: {"same_meaning": "yes" | "partly" | "no", "reason": "one short sentence"}"""


def judge_messages(question: str, reference: str, answer: str) -> list[dict[str, str]]:
    user = f"Question: {question}\n\nREFERENCE answer: {reference}\n\nAPP answer: {answer}"
    return [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]


def latest_e2e(split: str) -> tuple[str, dict]:
    files = sorted(REPORTS.glob(f"????-??-??-e2e-{split}.json"))
    if not files:
        raise SystemExit(f"no end-to-end report for {split}; run eval.run_e2e first")
    return files[-1].name, json.loads(files[-1].read_text(encoding="utf-8"))


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split", default="test", choices=["dev", "test"])
    args = ap.parse_args()

    s = get_settings()
    llm, model = LLMClients(s, cache_path=CACHE).for_role("judge2")
    items = {i.id: i for i in load_testset()}
    source, report = latest_e2e(args.split)
    rows, not_judged = [], []
    for r in report["rows"]:
        item = items.get(r["id"])
        if item is None:
            continue
        verdict, reason = None, None
        if r["group"] == "out_of_scope":
            verdict = "yes" if r["refused"] else "no"
        elif r["refused"]:
            verdict, reason = "no", f"refused ({r['refusal_reason']})"
        else:
            try:
                out = llm.chat_json(
                    model,
                    judge_messages(item.question, item.reference_answer, r["answer"]),
                    max_tokens=300,
                    reasoning_effort=s.judge2_reasoning,
                )
                verdict = str(out.get("same_meaning", "")).strip().lower()
                reason = out.get("reason")
            except LLMError as e:
                not_judged.append(r["id"])
                print(f"{r['id']} not judged: {str(e)[:80]}", flush=True)
                continue
        rows.append({"id": r["id"], "group": r["group"], "verdict": verdict, "reason": reason})

    by = defaultdict(list)
    for row in rows:
        by[row["group"]].append(row)
        if row["group"] != "out_of_scope":
            by["in_scope"].append(row)
    summary = {
        g: {
            "n": len(rs),
            "correct_strict": round(sum(r["verdict"] == "yes" for r in rs) / len(rs), 4),
            "correct_lenient": round(
                sum(r["verdict"] in ("yes", "partly") for r in rs) / len(rs), 4
            ),
        }
        for g, rs in by.items()
    }
    summary["not_run_end_to_end"] = len(report["summary"].get("not_run", []))
    summary["not_judged"] = not_judged
    summary["source"] = source
    out = REPORTS / f"{date.today().isoformat()}-answer-judge-{args.split}.json"
    out.write_text(json.dumps({"summary": summary, "rows": rows}, indent=1, ensure_ascii=False))
    for g in [*REPORT_GROUPS, "in_scope", "out_of_scope"]:
        if g in summary:
            v = summary[g]
            print(f"{g}: n={v['n']} strict {v['correct_strict']:.1%} "
                  f"lenient {v['correct_lenient']:.1%}")  # fmt: skip
    print(f"not run end to end: {summary['not_run_end_to_end']}; not judged: {len(not_judged)}")


if __name__ == "__main__":
    main()
