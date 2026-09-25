"""FBR Withholding Tax Rates Card for tax year 2027 (a guide, not law)."""

from datetime import date

from ingestion.laws.base import LawConfig

WHT_2027 = LawConfig(
    law="Withholding Tax Rates Card, Tax Year 2027",
    law_code="WHT",
    id_prefix="WHT2027",
    source_url="https://download1.fbr.gov.pk/Docs/202681113864992WithholdingTaxRatesCard2027.pdf",
    version_date=date(2026, 6, 30),  # "updated up to June 30, 2026 as per Finance Act, 2026"
)
