"""Income Tax Rules, 2002 — FBR consolidated text."""

from datetime import date

from ingestion.laws.base import LawConfig

# Pages after the rules (the First to Fourth Schedules) are blank forms, notices and
# return templates, so only the rules themselves are indexed (see docs/DECISIONS.md).
ITR_2002 = LawConfig(
    law="Income Tax Rules, 2002",
    law_code="ITR",
    id_prefix="ITR2002",
    source_url="https://download1.fbr.gov.pk/Docs/20269211394336470IncomeTaxRules2002.pdf",
    index_page_url="https://www.fbr.gov.pk/categ/income-tax-rules-2002/335",
    version_date=date(2026, 9, 15),
    body_header_regex=r"^CHAPTER\s*[-–]",
    body_end_regex=r"^PART\s*[-–]\s*[IVX]",
    include_schedules=False,
    unit_name="Rule",
    unit_code="r",
    header_max_y=120.0,
    footer_min_y=675.0,
    running_text_min_size=9.0,  # appendix headers ("PART-II FIRST SCHEDULE") are 9.5pt
    heading_max_x=175.0,  # some rule numbers are indented (e.g. 78N at x=168)
    separator_x=126.0,
    centered_min_x=220.0,
)
