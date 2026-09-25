"""Pydantic models shared by the parse and chunk steps."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field


class Line(BaseModel):
    """One visual line of body text (spans on the same baseline merged left-to-right)."""

    page: int = Field(description="1-based PDF page index")
    y: float
    x: float
    text: str
    bold_start: bool = Field(description="True when the first real span is bold")
    size: float = Field(description="Dominant font size of the line")
    fn_refs: list[str] = Field(default_factory=list, description="Footnote markers on this line")
    kind: Literal["text", "table"] = "text"


class Footnote(BaseModel):
    page: int
    marker: str
    text: str


class ParsedPage(BaseModel):
    page: int
    header: str
    printed_page: str | None = None
    lines: list[Line]
    footnotes: list[Footnote] = Field(default_factory=list)


class Chunk(BaseModel):
    chunk_id: str
    section_id: str = Field(description="Citation target shared by all pieces of one section")
    snapshot_id: str
    law: str
    law_code: str
    kind: Literal["section", "schedule_clause", "schedule_part", "table"]
    chapter: str | None = None
    part: str | None = None
    section: str | None = None
    subsection: str | None = None
    schedule: str | None = None
    clause: str | None = None
    title: str
    text: str
    amended_by: list[str] = Field(default_factory=list)
    amendment_notes: list[str] = Field(default_factory=list)
    tax_year_from: int
    tax_year_to: int | None = None
    source_url: str
    page: int
    page_end: int
    version_date: date
    n_tokens: int
    needs_review: bool = False
