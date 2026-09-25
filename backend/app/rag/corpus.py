"""Load the processed chunks of every law, and build the text that gets embedded."""

from pathlib import Path

from ingestion.models import Chunk

PROCESSED = Path("data/processed")


def load_chunks(root: Path = PROCESSED, laws: list[str] | None = None) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(root.glob("*/*/chunks.jsonl")):
        if laws and path.parent.parent.name not in laws:
            continue
        with path.open(encoding="utf-8") as fh:
            chunks += [Chunk.model_validate_json(line) for line in fh]
    return chunks


def embedding_text(chunk: Chunk) -> str:
    """Chunk text with a one-line context header (law, unit number, title).

    A piece like "(3) In case of association of persons..." means little on its own; the
    header tells the embedding model which law and section it belongs to.
    """
    unit = {"ITR": "Rule", "WHT": "Rate card, section"}.get(chunk.law_code, "Section")
    where = chunk.clause or chunk.section or ""
    if chunk.schedule:
        head = f"{chunk.law} — {chunk.title}"
    else:
        head = f"{chunk.law} — {unit} {where}" + (f": {chunk.title}" if chunk.title else "")
    return f"{head}\n{chunk.text}"
