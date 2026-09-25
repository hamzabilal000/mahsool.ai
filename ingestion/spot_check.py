"""Write a markdown report of N random chunks next to the PDF page they came from.

The plan asks for a manual check of 20 random chunks per law. This script picks them with
a fixed seed (so the sample is reproducible), and prints what to look for.

Usage:
    python -m ingestion.spot_check --law ITO2001 --n 20
"""

import argparse
import random
from pathlib import Path

from ingestion.chunk import processed_dir
from ingestion.laws import LAWS
from ingestion.models import Chunk

CHECKLIST = """For each chunk, tick if:
- [ ] text matches the PDF page (no missing lines, no text from another section)
- [ ] no footnote / repealed text leaked into the body
- [ ] title, section / clause number and page are right
- [ ] `amended_by` matches the footnotes on that page
"""


def load_chunks(path: Path) -> list[Chunk]:
    with path.open(encoding="utf-8") as fh:
        return [Chunk.model_validate_json(line) for line in fh]


def render(chunks: list[Chunk], pdf_url: str) -> str:
    out = [f"# Spot check — {chunks[0].snapshot_id}", "", CHECKLIST]
    for i, c in enumerate(chunks, start=1):
        out += [
            f"## {i}. `{c.chunk_id}` — {c.title}",
            f"kind: {c.kind} · pages {c.page}–{c.page_end} ([open PDF]({pdf_url}#page={c.page}))"
            f" · {c.n_tokens} tokens · needs_review: {c.needs_review}",
            f"amended_by: {', '.join(c.amended_by) or '—'}",
            "",
            "```text",
            c.text[:1500] + (" …" if len(c.text) > 1500 else ""),
            "```",
            "",
        ]
    return "\n".join(out)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--law", default="ITO2001", choices=sorted(LAWS))
    ap.add_argument("--n", type=int, default=20)
    ap.add_argument("--seed", type=int, default=2026)
    args = ap.parse_args()
    cfg = LAWS[args.law]

    folder = processed_dir(cfg)
    chunks = load_chunks(folder / "chunks.jsonl")
    sample = random.Random(args.seed).sample(chunks, min(args.n, len(chunks)))
    sample.sort(key=lambda c: c.page)
    out = folder / "spot_check.md"
    out.write_text(render(sample, cfg.source_url), encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
