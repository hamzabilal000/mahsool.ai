from ingestion.chunk import (
    Chunker,
    Para,
    estimate_tokens,
    extract_title,
    lines_to_paras,
    pack,
    section_key,
    split_table,
)
from ingestion.models import Footnote
from tests.ingestion.conftest import line, page

CH = "Chapter X – Procedure"


def run(cfg, pages, max_tokens: int = 800):
    return Chunker(cfg, pages, max_tokens).run()


def test_extract_title_variants() -> None:
    assert extract_title("149. Salary.— (1) Every person") == "Salary"
    assert extract_title("[5AA. Tax on return on investments in sukuks.—(1) Subject") == (
        "Tax on return on investments in sukuks"
    )
    assert extract_title("113. Minimum tax on the income of certain persons.- (1) This") == (
        "Minimum tax on the income of certain persons"
    )
    # hyphens inside words are not title separators
    assert extract_title("78. Non-arm’s length transactions.— Where an asset") == (
        "Non-arm’s length transactions"
    )


def test_section_key_orders_lettered_sections() -> None:
    nums = ["4", "4A", "4AB", "4B", "5", "100", "100A"]
    assert sorted(nums, key=section_key) == nums


def test_chapter_divisions_are_tracked_per_section(cfg) -> None:
    pages = [
        page(
            1,
            CH,
            [
                line(1, 10, "PART V", x=220, bold=True),
                line(1, 20, "ADVANCE TAX AND DEDUCTION OF TAX AT SOURCE", x=160, bold=True),
                line(1, 30, "Division I", x=220, bold=True),
                line(1, 40, "Advance Tax Paid by the Taxpayer", x=200, bold=True),
                line(1, 50, "147. Advance tax paid by the taxpayer.—(1) Text.", bold=True),
                line(1, 60, "Division III", x=220, bold=True),
                line(1, 70, "Deduction of Tax at Source", x=200, bold=True),
                line(1, 80, "149. Salary.—(1) Text.", bold=True),
            ],
        )
    ]
    s147, s149 = run(cfg, pages)
    assert s147.part == (
        "Part V: Advance Tax and Deduction of Tax at Source; "
        "Division I: Advance Tax Paid by the Taxpayer"
    )
    assert s149.part.endswith("; Division III: Deduction of Tax at Source")


def test_one_chunk_per_section_with_metadata(cfg) -> None:
    pages = [
        page(
            1,
            CH,
            [
                line(
                    1,
                    60,
                    "148. Imports.—(1) The Collector of Customs shall collect advance tax.",
                    bold=True,
                ),
                line(1, 72, "(2) The tax shall be collected at the rate specified.", refs=["1"]),
                line(
                    1, 90, "149. Salary.—(1) Every person responsible for paying salary", bold=True
                ),
                line(1, 102, "shall deduct tax.", x=99),
            ],
            footnotes=[Footnote(page=1, marker="1", text="Substituted by the Finance Act, 2025.")],
        )
    ]
    chunks = run(cfg, pages)
    assert [c.chunk_id for c in chunks] == ["TST2001-s148", "TST2001-s149"]
    s148, s149 = chunks
    assert s148.title == "Imports"
    assert s148.amended_by == ["Finance Act, 2025"]
    assert s148.tax_year_from == 2027
    assert s148.chapter == CH
    assert (
        s149.text == "149. Salary.—(1) Every person responsible for paying salary shall deduct tax."
    )
    assert s149.amended_by == []


def test_section_numbers_must_increase(cfg) -> None:
    """A bold '12.' inside section 149 (e.g. a list item) must not start a new section."""
    pages = [
        page(
            1,
            CH,
            [
                line(1, 60, "149. Salary.—(1) Text.", bold=True),
                line(1, 72, "12. Something that looks like a heading", bold=True),
            ],
        )
    ]
    chunks = run(cfg, pages)
    assert [c.section for c in chunks] == ["149"]
    assert "12. Something" in chunks[0].text


def test_long_section_splits_at_subsections_and_repeats_title(cfg) -> None:
    body = "word " * 150  # ~190 tokens per sub-section
    lines = [line(1, 50, "2. Definitions.— In this Ordinance —", bold=True)]
    lines += [line(1, 60 + i, f"({i}) {body}") for i in range(1, 9)]
    chunks = run(cfg, [page(1, CH, lines)], max_tokens=500)
    assert len(chunks) > 1
    assert all(c.n_tokens <= 500 for c in chunks)
    assert chunks[0].chunk_id == "TST2001-s2-1"
    assert {c.section_id for c in chunks} == {"TST2001-s2"}
    for c in chunks[1:]:
        assert c.text.startswith("Section 2. Definitions (continued)\n(")
    assert chunks[0].subsection == "(1)-(2)"


def test_centered_part_headings_are_metadata_not_text(cfg) -> None:
    pages = [
        page(
            1,
            CH,
            [
                line(1, 40, "PART II", x=220, bold=True),
                line(1, 45, "HEAD OF INCOME SALARY", x=200, bold=True),
                line(1, 60, "12. Salary.—(1) Any salary", bold=True),
            ],
        )
    ]
    (c,) = run(cfg, pages)
    assert c.part == "Part II: Head of Income Salary"
    assert "HEAD OF INCOME" not in c.text


def test_second_schedule_one_chunk_per_clause(cfg) -> None:
    sched = "Second Schedule – Part-I"
    pages = [
        page(
            1,
            sched,
            [
                line(1, 60, "(12) Any payment in the nature of commutation of pension.", bold=True),
                line(1, 72, "(i) sub-clause text", x=100),
                line(1, 90, "[(13) Any income representing gratuity", bold=True),
            ],
        )
    ]
    chunks = run(cfg, pages)
    assert [c.chunk_id for c in chunks] == ["TST2001-sch2-pI-cl12", "TST2001-sch2-pI-cl13"]
    assert chunks[0].clause == "(12)"
    assert chunks[0].kind == "schedule_clause"
    assert "(i) sub-clause text" in chunks[0].text


def test_schedule_tables_become_own_chunks_with_caption(cfg) -> None:
    table = "| S. No. | Taxable income | Rate |\n|---|---|---|\n| 1. | up to 600,000 | 0% |"
    pages = [
        page(
            1,
            "First Schedule – Part I",
            [
                line(1, 40, "Division I", x=220, bold=True),
                line(1, 50, "(1) The rates of tax shall be as set out in the following table:"),
                line(1, 60, table, kind="table"),
            ],
        )
    ]
    chunks = run(cfg, pages)
    tables = [c for c in chunks if c.kind == "table"]
    assert [c.chunk_id for c in tables] == ["TST2001-sch1-pI-divI-t1"]
    assert "following table" in tables[0].text and "| 1. | up to 600,000 | 0% |" in tables[0].text
    assert tables[0].section_id == "TST2001-sch1-pI-divI"
    assert tables[0].needs_review


def test_lines_to_paras_joins_wrapped_lines_and_hyphens() -> None:
    paras = lines_to_paras(
        [
            line(1, 10, "(1) A person shall be non-"),
            line(1, 20, "resident if the person is not"),
            line(1, 30, "resident."),
            line(1, 40, "Provided that [ ] this applies."),
        ]
    )
    assert [p.text for p in paras] == [
        "(1) A person shall be non-resident if the person is not resident.",
        "Provided that this applies.",
    ]


def test_table_continued_on_next_page_is_merged() -> None:
    first = "| S. No. | Income |\n|---|---|\n| 1. | a |"
    second = "| 2. | b |\n|---|---|\n| 3. | c |"
    paras = lines_to_paras([line(1, 10, first, kind="table"), line(2, 10, second, kind="table")])
    assert len(paras) == 1
    assert paras[0].text.endswith("| 1. | a |\n| 2. | b |\n| 3. | c |")


def test_split_table_repeats_header() -> None:
    rows = "\n".join(f"| {i}. | {'x' * 60} |" for i in range(40))
    pieces = split_table(Para(f"| S. No. | Text |\n|---|---|\n{rows}", {1}, is_table=True), 200)
    assert len(pieces) > 1
    assert all(p.text.startswith("| S. No. | Text |\n|---|---|") for p in pieces)
    assert all(estimate_tokens(p.text) <= 200 for p in pieces)


def test_pack_keeps_subsections_together() -> None:
    # (1) + its clause (a) ≈ 127 tokens stay together; (2) goes to the next piece.
    paras = [
        Para("(1) " + "a " * 150, {1}),
        Para("(a) " + "b " * 100, {1}),
        Para("(2) " + "c " * 20, {1}),
    ]
    groups = pack(paras, max_tokens=130, budget_reserve=0)
    assert [len(g) for g in groups] == [2, 1]
