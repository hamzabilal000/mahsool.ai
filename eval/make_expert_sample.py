"""Write eval/expert_sample.json: 30 random test questions for a human tax expert (DECISIONS D38).

The sample is stratified: each reporting group (english, fbr, urdu, roman_urdu, out_of_scope)
gets a share of the 30 proportional to its size on the test split (largest remainder, at least
one each), and questions are drawn at random within the group with a fixed seed, so re-running
gives the same sample for the same test set.

Usage:
    python -m eval.make_expert_sample
"""

import json
import random
from collections import defaultdict
from datetime import date
from pathlib import Path

from eval.run_eval import report_group
from eval.validate_testset import load_testset

OUT = Path(__file__).resolve().parent / "expert_sample.json"
SIZE = 30
SEED = 2027
GROUPS = ["english", "fbr", "urdu", "roman_urdu", "out_of_scope"]


def allocate(sizes: dict[str, int], total: int) -> dict[str, int]:
    """Proportional allocation with at least one per group; remainders go to the largest."""
    n = sum(sizes.values())
    exact = {g: total * s / n for g, s in sizes.items()}
    share = {g: max(1, int(x)) for g, x in exact.items()}
    by_remainder = sorted(sizes, key=lambda g: (exact[g] - int(exact[g]), sizes[g]), reverse=True)
    i = 0
    while sum(share.values()) < total:
        share[by_remainder[i % len(by_remainder)]] += 1
        i += 1
    return share


def main() -> None:
    by_group = defaultdict(list)
    for item in load_testset():
        if item.split == "test":
            by_group[report_group(item)].append(item)
    share = allocate({g: len(by_group[g]) for g in GROUPS}, SIZE)
    rng = random.Random(SEED)
    sample = []
    for g in GROUPS:
        for item in rng.sample(sorted(by_group[g], key=lambda i: i.id), share[g]):
            sample.append(
                {
                    "id": item.id,
                    "group": g,
                    "question": item.question,
                    "gold_section_ids": item.gold_section_ids,
                    "reference_answer": item.reference_answer,
                    "verified": item.verified,
                    "expert_ok": None,
                    "expert_notes": None,
                }
            )
    out = {
        "created": date.today().isoformat(),
        "seed": SEED,
        "stratified_by": GROUPS,
        "test_split_sizes": {g: len(by_group[g]) for g in GROUPS},
        "sample_sizes": share,
        "instructions": (
            "For each question, read the gold section(s) and set expert_ok to true if the "
            "reference answer is correct and complete enough, false otherwise (explain in "
            "expert_notes)."
        ),
        "questions": sample,
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"{len(sample)} questions → {OUT.name}: {share}")


if __name__ == "__main__":
    main()
