import pytest

from ingestion.amendments import laws_in_footnote, note_summary, sort_laws


@pytest.mark.parametrize(
    ("footnote", "expected"),
    [
        ("Inserted by the Finance Act, 2003.", ["Finance Act, 2003"]),
        ("Omitted by Finance Act 2014", ["Finance Act, 2014"]),
        (
            "Substituted by Finance (amendment) Ordinance, 2009",
            ["Finance (Amendment) Ordinance, 2009"],
        ),
        (
            "through Finance Supplementary (Second Amendment) Act, 2019",
            ["Finance Supplementary (Second Amendment) Act, 2019"],
        ),
        (
            "substituted through Tax Laws (Second Amendment), 2019 dated 26th December, 2019.",
            ["Tax Laws (Second Amendment), 2019"],
        ),
        (
            "Added by the Income Tax (Fourth Amendment) Act, 2016 dated 02.12.2016.",
            ["Income Tax (Fourth Amendment) Act, 2016"],
        ),
        ("Inserted by S.R.O. 389(I)/2009, dated 19.05.2009.", ["SRO 389(I)/2009"]),
        (
            "omitted by the Presidential Order No.F.2(1)/2016-Pub dated 31.08.2016.",
            ["Presidential Order No. F.2(1)/2016-Pub"],
        ),
    ],
)
def test_laws_in_footnote(footnote: str, expected: list[str]) -> None:
    assert laws_in_footnote(footnote) == expected


def test_the_law_itself_is_not_an_amending_law() -> None:
    assert laws_in_footnote("as defined in the Income Tax Ordinance, 2001") == []


def test_laws_inside_quoted_old_text_are_ignored() -> None:
    fn = (
        "Section 5A substituted by the Finance Act, 2017. The substituted section read as "
        "follows: “5A. ... inserted by the Finance Act, 2015 ...”"
    )
    assert laws_in_footnote(fn) == ["Finance Act, 2017"]


def test_note_summary_drops_quoted_old_text() -> None:
    fn = "Clause (8) omitted by the Finance Act 2025. The omitted clause read as follows: “(8) Any”"
    assert note_summary(fn) == "Clause (8) omitted by the Finance Act 2025. The omitted clause"


def test_sort_laws_newest_first() -> None:
    assert sort_laws({"Finance Act, 2019", "Finance Act, 2025", "SRO 389(I)/2009"}) == [
        "Finance Act, 2025",
        "Finance Act, 2019",
        "SRO 389(I)/2009",
    ]
