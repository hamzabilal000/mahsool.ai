from ingestion.chunk import Chunker
from tests.ingestion.conftest import line, page


def test_uppercase_division_heading_starts_a_new_unit_and_resets_per_part(cfg) -> None:
    pages = [
        page(
            1,
            "First Schedule – Part IV",
            [
                line(
                    1,
                    40,
                    "[Division XVIII Advance tax on purchase ... shall be 1.25%.] [ ### ]",
                    x=200,
                    bold=True,
                ),
                line(
                    1,
                    60,
                    "[DIVISION XXVII Advance tax on card remittances ... 0.5%.]",
                    x=200,
                    bold=True,
                ),
            ],
        ),
        page(2, "First Schedule – Part V", [line(2, 40, "Text of Part V.")]),
    ]
    chunks = Chunker(cfg, pages, 800).run()
    ids = [c.section_id for c in chunks]
    assert ids == ["TST2001-sch1-pIV-divXVIII", "TST2001-sch1-pIV-divXXVII", "TST2001-sch1-pV"]
    assert "###" not in chunks[0].text
