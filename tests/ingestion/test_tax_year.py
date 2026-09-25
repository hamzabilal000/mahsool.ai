from datetime import date

import pytest

from ingestion.tax_year import tax_year_in_force, tax_year_of


@pytest.mark.parametrize(
    ("day", "expected"),
    [(date(2026, 6, 30), 2026), (date(2026, 7, 1), 2027), (date(2027, 1, 15), 2027)],
)
def test_tax_year_of(day: date, expected: int) -> None:
    assert tax_year_of(day) == expected


def test_text_amended_up_to_30_june_governs_next_tax_year() -> None:
    assert tax_year_in_force(date(2026, 6, 30)) == 2027


def test_mid_year_amendment_stays_in_current_tax_year() -> None:
    assert tax_year_in_force(date(2026, 2, 20)) == 2026
