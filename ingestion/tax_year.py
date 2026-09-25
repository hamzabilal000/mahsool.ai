"""Pakistani tax-year arithmetic.

Under section 74 of the Income Tax Ordinance, a (normal) tax year is the 12 months ending
on 30 June and is named after the calendar year in which it ends: tax year 2027 runs
1 July 2026 – 30 June 2027.
"""

from datetime import date, timedelta


def tax_year_of(day: date) -> int:
    """Tax year that contains `day`."""
    return day.year + 1 if day.month >= 7 else day.year


def tax_year_in_force(version_date: date) -> int:
    """First tax year a consolidated text 'amended up to <version_date>' governs.

    FBR's cut-off is the last day before the new provisions apply, so the text governs the
    tax year that starts the next day. 'Amended up to 30.06.2026' → tax year 2027.
    """
    return tax_year_of(version_date + timedelta(days=1))
