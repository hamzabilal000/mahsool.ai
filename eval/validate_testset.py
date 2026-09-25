"""Validate eval/testset.jsonl against the schema and the current chunk index.

Checks: schema, unique ids, every gold section id exists in the chunks, translated items
share the split of their source question, and prints counts per group / split.

Usage:
    python -m eval.validate_testset
"""

import sys
from collections import Counter
from pathlib import Path

from eval.schema import TestItem
from ingestion.chunk import processed_dir
from ingestion.laws import LAWS
from ingestion.models import Chunk

ROOT = Path(__file__).resolve().parents[1]
TESTSET = ROOT / "eval" / "testset.jsonl"


def load_testset(path: Path = TESTSET) -> list[TestItem]:
    with path.open(encoding="utf-8") as fh:
        return [TestItem.model_validate_json(line) for line in fh if line.strip()]


def known_section_ids() -> set[str]:
    ids: set[str] = set()
    for cfg in LAWS.values():
        path = ROOT / processed_dir(cfg) / "chunks.jsonl"
        if path.exists():
            with path.open(encoding="utf-8") as fh:
                ids |= {Chunk.model_validate_json(line).section_id for line in fh}
    return ids


def validate(items: list[TestItem], section_ids: set[str]) -> list[str]:
    errors: list[str] = []
    dupes = [k for k, v in Counter(i.id for i in items).items() if v > 1]
    if dupes:
        errors.append(f"duplicate ids: {dupes}")
    by_id = {i.id: i for i in items}
    for item in items:
        missing = [g for g in item.gold_section_ids if g not in section_ids]
        if missing:
            errors.append(f"{item.id}: unknown gold section ids {missing}")
        if item.group != "out_of_scope" and not item.gold_section_ids:
            errors.append(f"{item.id}: in-scope question without gold sections")
        if item.group == "out_of_scope" and item.gold_section_ids:
            errors.append(f"{item.id}: out-of-scope question must have no gold sections")
        src = by_id.get(item.source_id) if item.source_id else None
        if item.source_id and src is None:
            errors.append(f"{item.id}: source_id {item.source_id} not found")
        if src and src.split != item.split:
            errors.append(f"{item.id}: split {item.split} differs from source {src.id}")
    return errors


def main() -> None:
    items = load_testset()
    errors = validate(items, known_section_ids())
    counts = Counter((i.group, i.split) for i in items)
    for (group, split), n in sorted(counts.items()):
        print(f"{group:13s} {split:5s} {n:4d}")
    print(f"total {len(items)} · verified {sum(i.verified for i in items)}")
    if errors:
        print("\n".join(errors))
        sys.exit(1)
    print("ok")


if __name__ == "__main__":
    main()
