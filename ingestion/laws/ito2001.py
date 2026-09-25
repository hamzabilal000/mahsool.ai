"""Income Tax Ordinance, 2001 — FBR consolidated text."""

from datetime import date

from ingestion.laws.base import LawConfig

# FBR lists every consolidated version on the index page. The latest one at the time of
# writing is "Amended upto 30.06.2026" (includes the Finance Act, 2026 → tax year 2027).
ITO_2001 = LawConfig(
    law="Income Tax Ordinance, 2001",
    law_code="ITO",
    id_prefix="ITO2001",
    source_url="https://download1.fbr.gov.pk/Docs/2026724177725705IncomeTaxOrdinanace2001.pdf",
    index_page_url="https://www.fbr.gov.pk/Categ/Income-Tax-Ordinance/326",
    version_date=date(2026, 6, 30),
    # The PDF prints "[[4AB] Subject to this Ordinance, a surcharge…" with no heading
    # (DECISIONS D37).
    title_overrides={"4AB": "Surcharge"},
)
