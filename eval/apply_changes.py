"""Apply eval/review/changes.json to eval/testset.jsonl and sync every translation to its source.

Each change replaces an English (or FBR) question's reference answer, and optionally its gold and
acceptable sections, with a version checked against the law text ("basis"). Urdu and Roman Urdu
translations share their source's reference answer and sections (D18), so they are overwritten
from the source every run; a fix can no longer miss a translation. The first run stores the old
answer in "before", so eval/FLAGGED.md can list every change with before and after.

Usage:
    python -m eval.apply_changes
"""

import json
from pathlib import Path

from eval.validate_testset import TESTSET

CHANGES = Path(__file__).resolve().parent / "review" / "changes.json"
SHARED = ("reference_answer", "gold_section_ids", "acceptable_section_ids", "tax_year", "split")


def load_changes() -> list[dict]:
    return json.loads(CHANGES.read_text(encoding="utf-8")) if CHANGES.exists() else []


def apply(rows: list[dict], changes: list[dict]) -> tuple[list[str], list[str]]:
    """(ids changed, translations synced). Fills "before" in `changes` on first application."""
    by_id = {r["id"]: r for r in rows}
    changed = []
    for c in changes:
        row = by_id[c["id"]]
        if row.get("source_id"):
            raise ValueError(f"{c['id']} is a translation; change its source {row['source_id']}")
        c.setdefault("before", row["reference_answer"])
        for key in ("reference_answer", "gold_section_ids", "acceptable_section_ids"):
            if key in c and row[key] != c[key]:
                row[key] = c[key]
                changed.append(c["id"])
    synced = []
    for row in rows:
        src = by_id.get(row.get("source_id") or "")
        if src and any(row[k] != src[k] for k in SHARED):
            for k in SHARED:
                row[k] = src[k]
            synced.append(row["id"])
    return sorted(set(changed)), synced


def main() -> None:
    rows = [json.loads(line) for line in TESTSET.read_text(encoding="utf-8").splitlines()]
    changes = load_changes()
    changed, synced = apply(rows, changes)
    TESTSET.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), "utf-8")
    CHANGES.write_text(json.dumps(changes, indent=1, ensure_ascii=False) + "\n", "utf-8")
    print(f"changed {len(changed)}: {', '.join(changed) or '-'}")
    print(f"translations synced {len(synced)}: {', '.join(synced) or '-'}")


if __name__ == "__main__":
    main()
