"""Check the ATL companions (D63): do answers about rates get the Tenth Schedule rule they need?

For every in-scope question of a split, runs the /ask search (cached rewrites and reranker
scores, no answer model) and lists the companion sources the answer model would get after the top
`answer_top_k`. A question "needs" the rule when its reference answer or question is about ATL /
non-ATL / filer status, or when a rate-card row is among its gold or acceptable sources. Reports:

- needs the rule and gets it (rule 1 or the rule 10 exception list) among its answer sources;
- extra sources added to questions that do not need them (prompt cost);
- the two live examples from D63.

Usage:
    python -m eval.atl_check --split dev
"""

import argparse
import re

from backend.app.config import get_settings
from eval.run_e2e import build_service
from eval.validate_testset import load_testset

RULE_IDS = {"ITO2001-sch10-1", "ITO2001-sch10-4"}
ATL_TEXT = re.compile(r"non[- ]?ATL|\bATL\b|Active Taxpayers|non[- ]?filer|\bfiler|Tenth Schedule",
                      re.IGNORECASE)  # fmt: skip
LIVE = [
    "What is the withholding tax on profit on debt paid by a bank to a filer?",
    "bank munafa par kitna tax katta hai agar main non filer hun?",
]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    args = ap.parse_args()
    k = get_settings().answer_top_k
    service = build_service()
    pipeline = service.pipeline

    def sources(question: str) -> tuple[list[str], list[str]]:
        result = pipeline.search(question)
        top = [c.chunk_id for c in result.candidates[:k]]
        return top, [c.chunk_id for c in pipeline.companions(result, k)]

    needs_ok, needs_total, extra_cost, with_extra = [], 0, 0, 0
    items = [i for i in load_testset() if i.split == args.split and i.gold_section_ids]
    for item in items:
        top, extra = sources(item.question)
        # A rate-card row is gold or acceptable: the rate differs (or not) by ATL status.
        card_gold = any(s.startswith("WHT") for s in item.gold_section_ids +
                        item.acceptable_section_ids)  # fmt: skip
        needs = bool(ATL_TEXT.search(item.question + " " + item.reference_answer)) or card_gold
        has_rule = bool(RULE_IDS & set(top + extra))
        with_extra += bool(extra)
        if needs:
            needs_total += 1
            if has_rule:
                needs_ok.append(item.id)
            else:
                print(f"  MISSING rule: {item.id} top={top} extra={extra}")
        elif extra:
            extra_cost += len(extra)
            print(f"  extra without need: {item.id} {extra}")
    print(f"\n{args.split}: {len(items)} in-scope questions, {with_extra} get companions")
    print(f"needs the Tenth Schedule rule: {needs_total}; has it among its answer sources: "
          f"{len(needs_ok)} ({len(needs_ok) / max(needs_total, 1):.0%})")  # fmt: skip
    print(f"companions on questions that do not need them: {extra_cost}")
    for q in LIVE:
        top, extra = sources(q)
        print(f"\nlive: {q}\n  top: {top}\n  companions: {extra}")
    pipeline.retriever.store.client.close()


if __name__ == "__main__":
    main()
