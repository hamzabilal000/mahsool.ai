from ingestion.download import find_versions
from ingestion.parse import _table_markdown


def test_table_compacts_misaligned_columns_and_splits_stacked_tables() -> None:
    rows = [
        ["(1) The rates of tax for individuals shall be as set out in the following table", "", ""],
        ["S. No.", "Taxable income", "", "Rate"],
        ["1.", "up to 600,000", None, "0%"],
        ["(2) Where salary exceeds seventy-five per cent the following table applies", "", "", ""],
        ["S. No.", "", "Taxable income", "Rate"],
        ["1.", "", "up to 600,000", "0%"],
    ]
    tables = _table_markdown(rows)
    assert len(tables) == 2
    (cap1, md1), (cap2, md2) = tables
    assert cap1.startswith("(1) The rates") and cap2.startswith("(2) Where salary")
    assert md1.splitlines()[0] == "| S. No. | Taxable income | Rate |"
    assert md2.splitlines()[2] == "| 1. | up to 600,000 | 0% |"


def test_table_strips_inline_amendment_markers() -> None:
    ((_, md),) = _table_markdown([["S. No.", "Rate"], ["1.", "1[5%]"]])
    assert "| 1. | [5%] |" in md


def test_find_versions_newest_first() -> None:
    html = """
      <a href="https://x/old.pdf" target="_blank">ITO, 2001 Amended upto 20.02.2026</a>
      <a href="https://x/new.pdf">Income Tax Ordinance, 2001 Amended upto 30.06.2026</a>
      <a href="https://x/other.pdf">Some circular</a>
    """
    versions = find_versions(html)
    assert [v.url for v in versions] == ["https://x/new.pdf", "https://x/old.pdf"]
    assert versions[0].version_date.isoformat() == "2026-06-30"
