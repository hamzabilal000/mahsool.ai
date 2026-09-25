"""Request and response models for the HTTP API.

Every response uses the same envelope: {"success", "data", "error", "code"}.
"""

from typing import Generic, Literal, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")

RefusalReason = Literal[
    "OUT_OF_SCOPE",  # provincial tax, customs, not about tax ...
    "TAX_YEAR_NOT_COVERED",  # no law text loaded for that tax year
    "SECTION_NOT_FOUND",  # "section 999Z" does not exist
    "NO_RELEVANT_SOURCES",  # best reranker score below the threshold
    "NOT_IN_SOURCES",  # the answer model found no answer in the sources
    "NO_VALID_CITATIONS",  # the answer cited nothing that was retrieved
]


class Envelope(BaseModel, Generic[T]):
    success: bool
    data: T | None = None
    error: str | None = None
    code: str = Field(description="OK, REFUSED, or an error code such as VALIDATION_ERROR")


class AskRequest(BaseModel):
    question: str = Field(min_length=3, max_length=1000)
    tax_year: int | None = Field(
        default=None, ge=2003, le=2035, description="Defaults to the current tax year (TY2027)"
    )


class Citation(BaseModel):
    n: int = Field(description="The [n] marker used in the answer text")
    chunk_id: str
    section_id: str
    law: str
    label: str = Field(description="e.g. 'Income Tax Ordinance, 2001 — Section 149: Salary'")
    text: str
    page: int
    url: str = Field(description="FBR PDF link opened at the cited page")
    version_date: str


class Source(BaseModel):
    rank: int
    chunk_id: str
    section_id: str
    label: str
    via: Literal["lookup", "search"]
    rerank_score: float | None


class AskData(BaseModel):
    answer: str
    refused: bool
    refusal_reason: RefusalReason | None = None
    language: Literal["en", "ur", "roman_ur"]
    tax_year: int
    tax_year_assumed: bool
    confidence: Literal["high", "medium", "low"] | None = None
    citations: list[Citation] = []
    sources: list[Source] = Field(default=[], description="Retrieved chunks ('Show sources')")
    search_queries: list[str] = Field(default=[], description="English rewrites that were used")
    warnings: list[str] = []
    disclaimer: str
    timings_ms: dict[str, int] = {}
