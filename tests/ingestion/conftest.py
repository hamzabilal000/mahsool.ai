from datetime import date

import pytest

from ingestion.laws.base import LawConfig
from ingestion.models import Footnote, Line, ParsedPage


@pytest.fixture
def cfg() -> LawConfig:
    return LawConfig(
        law="Test Ordinance, 2001",
        law_code="TST",
        id_prefix="TST2001",
        source_url="https://example.test/law.pdf",
        version_date=date(2026, 6, 30),
    )


def line(
    page: int,
    y: float,
    text: str,
    *,
    x: float = 72.0,
    bold: bool = False,
    refs: list[str] | None = None,
    kind: str = "text",
) -> Line:
    return Line(
        page=page, y=y, x=x, text=text, bold_start=bold, size=10.0, fn_refs=refs or [], kind=kind
    )


def page(
    no: int, header: str, lines: list[Line], footnotes: list[Footnote] | None = None
) -> ParsedPage:
    return ParsedPage(page=no, header=header, lines=lines, footnotes=footnotes or [])
