"""Write eval/REVIEW.md: a checklist for verifying the unverified test questions by hand.

For each question it shows the question, the gold section ids, the first 300 characters of
each gold section and the reference answer, with checkboxes. Translations are listed under
their English source so the Urdu and Roman Urdu can be checked side by side.

Usage:
    python -m eval.make_review               # test split (default)
    python -m eval.make_review --split dev
"""

import argparse
from pathlib import Path

from backend.app.rag.corpus import load_chunks
from eval.schema import TestItem
from eval.validate_testset import load_testset

OUT = Path(__file__).resolve().parent / "REVIEW.md"
LANG = {"en": "English", "ur": "Urdu", "roman_ur": "Roman Urdu"}


def preview(text: str, n: int = 300) -> str:
    flat = " ".join(text.split())
    return flat if len(flat) <= n else flat[:n].rstrip() + " …"


def render(items: list[TestItem], split: str) -> str:
    first_chunk: dict[str, object] = {}
    for c in load_chunks():
        first_chunk.setdefault(c.section_id, c)

    todo = [i for i in items if i.split == split and not i.verified]
    by_source: dict[str, list[TestItem]] = {}
    for i in todo:
        if i.source_id:
            by_source.setdefault(i.source_id, []).append(i)
    translated_ids = {i.id for group in by_source.values() for i in group}
    roots = [i for i in todo if i.id not in translated_ids]
    in_scope = [i for i in roots if i.group != "out_of_scope"]
    oos = [i for i in roots if i.group == "out_of_scope"]

    lines = [
        f"# Eval review — {split} split",
        "",
        f"{len(todo)} unverified questions. For each one, tick the boxes that are true and note "
        "anything wrong. Then tell Claude Code which ids to fix; verified ones get "
        '`"verified": true` in `eval/testset.jsonl`.',
        "",
        "What to check:",
        "- **Gold is right:** the gold section really answers the question (open the PDF page if "
        "unsure).",
        "- **Reference answer is right** according to that section.",
        "- **Translation is natural:** the Urdu / Roman Urdu reads like something a person would "
        "actually type, and means the same as the English.",
        "",
        "Regenerate this file with `python -m eval.make_review`.",
        "",
        "## In-scope questions",
        "",
    ]
    for item in in_scope:
        lines += [f"### {item.id} · {item.type} · {item.difficulty}", "", f"> {item.question}", ""]
        for sid in item.gold_section_ids:
            c = first_chunk.get(sid)
            if c is None:
                lines.append(f"- **{sid}**: _section not found in the chunks_")
                continue
            url = f"{c.source_url}#page={c.page}"
            lines.append(f"- **{sid}** ([PDF p. {c.page}]({url})): {preview(c.text)}")
        if item.acceptable_section_ids:
            lines.append(f"- also acceptable: {', '.join(item.acceptable_section_ids)}")
        lines += [
            "",
            f"Reference answer: {item.reference_answer}",
            "",
            f"- [ ] {item.id}: gold section answers the question",
            f"- [ ] {item.id}: reference answer is correct",
        ]
        for t in by_source.get(item.id, []):
            lines += [
                f"- [ ] {t.id} ({LANG[t.language]}) reads naturally and means the same: "
                f"{t.question}"
            ]
        lines.append("")
    # Translations whose English source is in another split (should not happen; validator
    # enforces same split) would be missed above, so list any leftovers.
    root_ids = {i.id for i in roots}
    orphans = [i for sid, group in by_source.items() if sid not in root_ids for i in group]
    if orphans:
        lines += ["## Translations without an English source in this list", ""]
        lines += [f"- [ ] {i.id} ({LANG[i.language]}): {i.question}" for i in orphans]
        lines.append("")
    lines += [
        "## Out-of-scope questions (the correct answer is a refusal)",
        "",
        "Check that each one really is outside what Mahsool covers (Income Tax Ordinance, Rules "
        "and the withholding rate card).",
        "",
    ]
    lines += [
        f"- [ ] {i.id} ({LANG[i.language]}): {i.question} — _{i.reference_answer}_" for i in oos
    ]
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--split", default="test", choices=["dev", "test"])
    ap.add_argument("--out", type=Path, default=OUT)
    args = ap.parse_args()
    md = render(load_testset(), args.split)
    args.out.write_text(md, encoding="utf-8")
    print(f"wrote {args.out} ({md.count('- [ ]')} checkboxes)")


if __name__ == "__main__":
    main()
