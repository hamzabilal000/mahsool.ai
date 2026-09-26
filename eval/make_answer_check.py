"""Write eval/answer_check.md: 50 random app answers next to their reference answers, for a
person with no tax knowledge to mark "same meaning? yes / no" (the plan's 50 hand-checked answers).

Draws from the latest end-to-end report of the split: answered in-scope questions only, a fixed
seed, and never more than the answers that exist (the file says how many were available).

Usage:
    python -m eval.make_answer_check --split test
"""

import argparse
import random
from datetime import date
from pathlib import Path

from eval.judge_answers import latest_e2e
from eval.validate_testset import load_testset

OUT = Path(__file__).resolve().parent / "answer_check.md"
SIZE, SEED = 50, 2027


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split", default="test", choices=["dev", "test"])
    args = ap.parse_args()

    items = {i.id: i for i in load_testset()}
    source, report = latest_e2e(args.split)
    answered = sorted(
        (r for r in report["rows"] if r["group"] != "out_of_scope" and not r["refused"]),
        key=lambda r: r["id"],
    )
    sample = random.Random(SEED).sample(answered, min(SIZE, len(answered)))
    lines = [
        "# Answer check: does the app say the same as the reference?",
        "",
        f"Generated {date.today().isoformat()} from `eval/reports/{source}` "
        f"({len(sample)} of {len(answered)} answered test questions, seed {SEED}).",
        "",
        "For each question, read the **reference answer** and the **app answer**. Tick **yes** if "
        "they say the same thing (same rate, amount, condition and conclusion; wording may differ "
        "and extra correct detail is fine), otherwise **no**, and write a few words why. No tax "
        "knowledge is needed: compare the two texts only. Ignore citation markers like [1].",
        "",
    ]
    if len(sample) < SIZE:
        lines += [f"> Only {len(sample)} answers exist so far; re-generate after "
                  "`python -m eval.run_e2e --split test` has run more questions.", ""]  # fmt: skip
    for n, r in enumerate(sample, start=1):
        item = items[r["id"]]
        lines += [
            f"## {n}. {r['id']} ({r['group']})",
            "",
            f"**Question:** {item.question}",
            "",
            f"**Reference answer:** {item.reference_answer}",
            "",
            f"**App answer:** {r['answer']}",
            "",
            "Same meaning?  - [ ] yes  - [ ] no   Why (if no): ",
            "",
        ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"wrote {OUT} with {len(sample)} answers")


if __name__ == "__main__":
    main()
