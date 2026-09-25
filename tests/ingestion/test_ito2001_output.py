"""Regression tests on the committed ITO 2001 chunks (no PDF or network needed)."""

import json
from collections import Counter
from pathlib import Path

import pytest

from ingestion.models import Chunk

OUT = Path(__file__).resolve().parents[2] / "data/processed/ITO2001/2026-06-30"

pytestmark = pytest.mark.skipif(not (OUT / "chunks.jsonl").exists(), reason="run the pipeline")


@pytest.fixture(scope="module")
def chunks() -> list[Chunk]:
    with (OUT / "chunks.jsonl").open(encoding="utf-8") as fh:
        return [Chunk.model_validate_json(line) for line in fh]


@pytest.fixture(scope="module")
def report() -> dict:
    return json.loads((OUT / "report.json").read_text(encoding="utf-8"))


def test_every_live_section_in_the_toc_has_a_chunk(report) -> None:
    assert report["toc_live_missing"] == []
    assert report["sections_not_in_toc"] == []
    assert report["n_sections"] >= 370


def test_chunk_ids_are_unique(chunks) -> None:
    dupes = [k for k, v in Counter(c.chunk_id for c in chunks).items() if v > 1]
    assert dupes == []


def test_no_chunk_exceeds_the_token_budget(chunks) -> None:
    assert max(c.n_tokens for c in chunks) <= 800


def test_salary_section(chunks) -> None:
    (s149,) = [c for c in chunks if c.chunk_id == "ITO2001-s149"]
    assert s149.title == "Salary"
    assert s149.text.startswith("149. Salary.")
    assert "Finance Act, 2025" in s149.amended_by


def test_repealed_rate_tables_quoted_in_footnotes_are_not_indexed(chunks) -> None:
    """The pre-2019 Division I (29% top slab above Rs. 5 million) and the TY2026 salaried
    table (Rs. 616,000 + 35% above Rs. 4.1 million) survive only in footnotes."""
    text = "\n".join(c.text for c in chunks)
    assert "600,000 + 29% of the amount exceeding Rs. 5,000,000" not in text
    assert "616,000/- + 35%" not in text


def test_current_salaried_rate_table_is_present(chunks) -> None:
    div1 = [c for c in chunks if c.section_id == "ITO2001-sch1-pI-divI" and c.kind == "table"]
    text = "\n".join(c.text for c in div1)
    assert "seventy-five per cent" in text
    assert "Rs. 1,424,000/- + 35% of the amount exceeding Rs. 7,000,000" in text


def test_footnote_text_does_not_leak_into_sections(chunks) -> None:
    leaks = [
        c.chunk_id
        for c in chunks
        if any(
            p.startswith(("Inserted by the Finance Act", "Substituted by the Finance Act"))
            for p in c.text.split("\n")
        )
    ]
    assert leaks == []
