"""Per-law configuration: where the PDF lives and how its layout looks."""

from datetime import date

from pydantic import BaseModel, Field


class LawConfig(BaseModel):
    law: str = Field(description="Official name, e.g. 'Income Tax Ordinance, 2001'")
    law_code: str = Field(description="Short code used in metadata filters, e.g. 'ITO'")
    id_prefix: str = Field(description="Prefix for chunk IDs, e.g. 'ITO2001'")
    source_url: str = Field(description="Direct link to the consolidated PDF on FBR")
    index_page_url: str | None = Field(
        default=None, description="FBR page that lists every consolidated version"
    )
    version_date: date = Field(description="'Amended up to' date printed on the PDF")

    # Layout: running headers tell us which chapter / schedule a page belongs to.
    body_header_regex: str = r"^Chapter\s+[IVXL]+"
    schedule_header_regex: str = r"^(?P<ordinal>\w+)\s+Schedule"

    # Font geometry (PDF points) for this document.
    header_max_y: float = 55.0
    footer_min_y: float = 595.0
    running_text_min_size: float = 11.5  # headers / page numbers are 12pt
    junk_min_size: float = 20.0  # decorative ".." glyphs
    heading_max_x: float = 95.0  # section numbers start at the left margin

    @property
    def snapshot_id(self) -> str:
        return f"{self.id_prefix}@{self.version_date.isoformat()}"
