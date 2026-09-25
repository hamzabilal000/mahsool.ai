"""Regression tests on the committed Income Tax Rules and rate-card chunks."""

import json
from collections import Counter
from pathlib import Path

import pytest

from ingestion.models import Chunk

DATA = Path(__file__).resolve().parents[2] / "data/processed"
ITR = DATA / "ITR2002/2026-09-15"
WHT = DATA / "WHT2027/2026-06-30"


def load(folder: Path) -> list[Chunk]:
    if not (folder / "chunks.jsonl").exists():
        pytest.skip("run the pipeline")
    with (folder / "chunks.jsonl").open(encoding="utf-8") as fh:
        return [Chunk.model_validate_json(line) for line in fh]


def table_rows(chunks: list[Chunk], section: str) -> list[list[str]]:
    rows = []
    for c in chunks:
        if c.section == section:
            for line in c.text.splitlines():
                if line.startswith("| ") and not line.startswith("| Case"):
                    rows.append([cell.strip() for cell in line.strip("|").split("|")])
    return rows


def test_rules_cover_every_live_rule_in_the_toc() -> None:
    report = json.loads((ITR / "report.json").read_text(encoding="utf-8"))
    assert report["toc_live_missing"] == []
    assert report["sections_not_in_toc"] == []
    assert report["n_sections"] >= 370


def test_rules_ids_unique_and_within_budget() -> None:
    chunks = load(ITR)
    assert [k for k, v in Counter(c.chunk_id for c in chunks).items() if v > 1] == []
    assert max(c.n_tokens for c in chunks) <= 800
    assert all(c.chunk_id.startswith("ITR2002-r") for c in chunks)


def test_rules_do_not_contain_the_form_appendix() -> None:
    """The Schedules of forms start on PDF page 429 ("PART-I FIRST SCHEDULE")."""
    assert max(c.page_end for c in load(ITR)) < 429


def test_conveyance_rule_has_both_rates() -> None:
    (r5,) = [c for c in load(ITR) if c.section_id == "ITR2002-r5"]
    assert "5% of" in r5.text and "10% of" in r5.text


@pytest.mark.parametrize(
    ("section", "case_contains", "atl", "non_atl"),
    [
        ("148", "Goods falling in Part-I, Twelfth Schedule", "1.00%", "2.00%"),
        ("233", "Advertising agents", "10.00%", "20.00%"),
        ("236K", "does not exceed Rs. 50 million", "1.25%", "10.50%"),
        ("236G", "Other than fertilizers", "0.10%", "2.00%"),
        ("156", "Prize bond", "15.00%", "30.00%"),
    ],
)
def test_rate_card_rows(section: str, case_contains: str, atl: str, non_atl: str) -> None:
    rows = table_rows(load(WHT), section)
    match = [r for r in rows if case_contains in r[0]]
    assert match, f"no row containing {case_contains!r} in section {section}"
    assert match[0][1] == atl and match[0][2] == non_atl


def test_rate_card_salary_top_slab_matches_the_ordinance() -> None:
    rows = table_rows(load(WHT), "149")
    top = [r for r in rows if r[0].startswith("Where taxable income exceeds Rs. 7,000,000")]
    assert top and top[0][1].startswith("Rs. 1,424,000 + 35%")


def test_rate_card_covers_expected_sections() -> None:
    sections = {c.section for c in load(WHT)}
    assert {"148", "149", "153", "154A", "155", "231AB", "233", "236K", "236Y", "236Z"} <= sections
