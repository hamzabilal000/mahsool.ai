"""Parse FBR's Withholding Tax Rate Card into one table chunk per section.

The rate card is an Excel export: a six-column grid (Section | Ancillary Information A |
Ancillary Information B | ATL rate | Non-ATL rate | Reference). Merged cells make the
generic table finder return shifted columns, so instead:

  1. column boundaries come from the header row on each page;
  2. row boundaries come from the table finder's row boxes (the ruling lines);
  3. every word is placed into (row, column) by its centre point;
  4. rows with no description and no rate are continuations of the row above;
  5. rows are grouped by section number (blank Section cells inherit the one above).

The card is a convenience document — FBR states the Ordinance prevails over it — so every
chunk says so and points at the First Schedule reference given in the card.

Usage:
    python -m ingestion.ratecard --law WHT2027
"""

import argparse
import logging
import re
from dataclasses import dataclass
from itertools import pairwise

import pymupdf

from ingestion.chunk import Para, estimate_tokens, processed_dir, split_table
from ingestion.laws import LAWS, LawConfig
from ingestion.models import Chunk
from ingestion.parse import raw_pdf_path
from ingestion.settings import get_settings
from ingestion.tax_year import tax_year_in_force

log = logging.getLogger(__name__)

SECTION_CELL_RE = re.compile(
    r"^(?P<num>\d{1,3}[A-Z]{0,4})(?:\s*\((?P<sub>[^)]*)\))?\s*(?P<title>.*)$"
)
WS_RE = re.compile(r"\s+")
SECTION_LABEL_RE = re.compile(r"^\d{3}[A-Z]{0,3}\b")
CELL_GAP = 5.0  # pt of whitespace between two cells in the same column
HEADER_WORDS = ("Section", "Ancillary", "ATL", "Non-ATL", "Reference")
# A rate cell starts with a percentage, an amount, "Nil" or a cross-reference.
RATE_START_RE = re.compile(
    r"^(?:Rs\.?\s*\d|Nil\b|Same\b|[-–—]$|\d[\d.,]*\s*%|\d[\d.,]*\s*(?:and|&))"
)
CONNECTOR_END_RE = re.compile(r"(?:Rs\.?|exceeding|of|the|\+|to|for|plus|and|@|,)\s*$", re.I)


@dataclass
class Record:
    page: int
    section: str
    section_title: str
    description: str
    atl: str
    non_atl: str
    reference: str


def _cluster(values: list[float], tol: float = 3.0) -> list[float]:
    out: list[float] = []
    for v in sorted(values):
        if not out or v - out[-1] > tol:
            out.append(v)
    return out


def _horizontal_rules(page: pymupdf.Page) -> list[tuple[float, float, float]]:
    """(y, x0, x1) of every horizontal ruling segment on the page."""
    segs = []
    for drawing in page.get_drawings():
        for item in drawing["items"]:
            if item[0] == "l" and abs(item[1].y - item[2].y) < 1:
                x0, x1 = sorted((item[1].x, item[2].x))
                segs.append((item[1].y, x0, x1))
            elif item[0] == "re" and item[1].height < 2:
                segs.append((item[1].y0, item[1].x0, item[1].x1))
    return [s for s in segs if s[2] - s[1] > 20]


@dataclass
class _Line:
    x: float
    y0: float
    y1: float
    text: str


def _lines(page: pymupdf.Page) -> list[_Line]:
    out = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            text = WS_RE.sub(" ", "".join(s["text"] for s in line["spans"])).strip()
            if text:
                x0, y0, _x1, y1 = line["bbox"]
                out.append(_Line(x0, y0, y1, text))
    return sorted(out, key=lambda ln: (ln.y0, ln.x))


def _anchors(col_lines: list[_Line]) -> list[float]:
    """y of every line that starts a new rate (not the wrapped tail of the one above)."""
    ys: list[float] = []
    prev: _Line | None = None
    for ln in col_lines:
        starts_rate = RATE_START_RE.match(ln.text)
        wrapped = (
            prev is not None and ln.y0 - prev.y1 < CELL_GAP and CONNECTOR_END_RE.search(prev.text)
        )
        if starts_rate and not wrapped:
            ys.append(ln.y0)
        prev = ln
    return ys


def page_records(page: pymupdf.Page) -> list[Record] | None:
    words = page.get_text("words")
    header = [w for w in words if w[4] in ("Section", "Reference") and w[1] < 130]
    disclaimer = [w for w in words if w[4].startswith("Disclaimer")]
    segs = _horizontal_rules(page)
    if len(header) < 2:
        return None
    top = max(w[3] for w in header) + 10
    bottom = min(w[1] for w in disclaimer) - 2 if disclaimer else page.rect.height - 60
    # Column edges: the ruling-segment start nearest to each header's position (headings
    # sit ~8-30pt right of their cell edge; some pages have extra segments inside cells).
    heads = _cluster(sorted(w[0] for w in words if w[1] < 130 and w[4] in HEADER_WORDS), tol=20)
    if len(heads) != 6:
        return None
    seg_starts = _cluster([s[1] for s in segs if top - 20 < s[0] < bottom + 20])
    starts = [
        min((x for x in seg_starts if h - 40 <= x <= h + 2), key=lambda x: h - x, default=h - 8)
        for h in heads
    ]

    lines = [ln for ln in _lines(page) if top < (ln.y0 + ln.y1) / 2 < bottom]

    def col_of(ln: _Line) -> int:
        return sum(ln.x >= e - 3 for e in starts[1:])

    rate_lines = [ln for ln in lines if col_of(ln) in (3, 4)]
    anchors = _cluster(
        _anchors([ln for ln in rate_lines if col_of(ln) == 3])
        + _anchors([ln for ln in rate_lines if col_of(ln) == 4]),
        tol=4,
    )
    if not anchors:
        return None

    # Rows are top-aligned: a row starts where a description cell starts (cells are separated
    # by >= 8pt of whitespace, lines inside a cell by 2-3pt) or where a new rate starts.
    starts_y: list[float] = []
    for c in (1, 2):
        prev: _Line | None = None
        for ln in (ln for ln in lines if col_of(ln) == c):
            if prev is None or ln.y0 - prev.y1 > CELL_GAP:
                starts_y.append(ln.y0)
            prev = ln
    bounds = [top, *(y - 1 for y in _cluster(starts_y + anchors, tol=4) if y - 1 > top), bottom]

    # Section labels (column 0) and the rows they span.
    sec_rules = _cluster([s[0] for s in segs if s[1] < starts[1] and top < s[0] < bottom])
    labels = [ln for ln in lines if col_of(ln) == 0]
    label_groups: list[list[_Line]] = []
    for ln in labels:
        if (
            label_groups
            and ln.y0 - label_groups[-1][-1].y1 < 4
            and not SECTION_LABEL_RE.match(ln.text)
            and not any(label_groups[-1][-1].y1 <= y <= ln.y0 for y in sec_rules)
        ):
            label_groups[-1].append(ln)
        else:
            label_groups.append([ln])

    def section_for(row_top: float) -> tuple[str, str]:
        # Labels are top-aligned with their first row: take the last label at or above the
        # row, but never across a ruling line of the Section column.
        region = [top, *sec_rules, bottom]
        lo = max(v for v in region if v <= row_top + 2)
        above = [g for g in label_groups if lo - 2 <= g[0].y0 <= row_top + 3]
        if not above:
            return "", ""
        m = SECTION_CELL_RE.match(" ".join(ln.text for ln in above[-1]))
        return (m.group("num"), m.group("title").strip()) if m else ("", "")

    records = []
    for lo, hi in pairwise(bounds):
        cell = {
            c: " ".join(
                ln.text for ln in lines if col_of(ln) == c and lo <= (ln.y0 + ln.y1) / 2 < hi
            )
            for c in range(1, 6)
        }
        if not any(cell.values()):
            continue
        num, title = section_for(lo + 1)
        records.append(
            Record(
                page=page.number + 1,
                section=num,
                section_title=title,
                description=" — ".join(t for t in (cell[1], cell[2]) if t),
                atl=cell[3],
                non_atl=cell[4],
                reference=cell[5],
            )
        )
    return records


def parse_records(doc: pymupdf.Document) -> list[Record]:
    records: list[Record] = []
    for page in doc:
        page_recs = page_records(page)
        if page_recs is None:
            continue
        for r in page_recs:
            if not r.section and records:  # a section cell continued from the previous page
                r.section, r.section_title = records[-1].section, records[-1].section_title
            records.append(r)
    # A row with only a rate fragment is the wrapped tail of the row above.
    merged: list[Record] = []
    for r in records:
        if merged and not r.description and not r.reference and r.page == merged[-1].page:
            merged[-1].atl = f"{merged[-1].atl} {r.atl}".strip()
            merged[-1].non_atl = f"{merged[-1].non_atl} {r.non_atl}".strip()
            continue
        merged.append(r)
    return [r for r in merged if r.section]


def records_to_chunks(records: list[Record], cfg: LawConfig, max_tokens: int) -> list[Chunk]:
    groups: dict[str, list[Record]] = {}
    for r in records:
        groups.setdefault(r.section, []).append(r)

    chunks: list[Chunk] = []
    ty = tax_year_in_force(cfg.version_date)
    for section, recs in groups.items():
        title = next((r.section_title for r in recs if r.section_title), "") or f"Section {section}"
        header = (
            f"{cfg.law} — section {section} of the Income Tax Ordinance, 2001: {title}\n"
            "Rates for persons on the Active Taxpayers' List (ATL) and not on it (Non-ATL). "
            "FBR note: the Ordinance prevails over this card in case of any conflict."
        )
        md_rows = ["| Case | ATL rate | Non-ATL rate | Reference |", "|---|---|---|---|"]
        md_rows += [
            "| "
            + " | ".join(x or "—" for x in (r.description, r.atl, r.non_atl, r.reference))
            + " |"
            for r in recs
        ]
        table = Para("\n".join(md_rows), {r.page for r in recs}, is_table=True)
        pieces = split_table(table, max_tokens - estimate_tokens(header) - 10)
        for k, piece in enumerate(pieces, start=1):
            text = f"{header}\n{piece.text}"
            sid = f"{cfg.id_prefix}-s{section}"
            chunks.append(
                Chunk(
                    chunk_id=sid if len(pieces) == 1 else f"{sid}-{k}",
                    section_id=sid,
                    snapshot_id=cfg.snapshot_id,
                    law=cfg.law,
                    law_code=cfg.law_code,
                    kind="table",
                    section=section,
                    title=title,
                    text=text,
                    tax_year_from=ty,
                    tax_year_to=ty,
                    source_url=cfg.source_url,
                    page=min(r.page for r in recs),
                    page_end=max(r.page for r in recs),
                    version_date=cfg.version_date,
                    n_tokens=estimate_tokens(text),
                    needs_review=True,
                )
            )
    return chunks


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--law", default="WHT2027", choices=sorted(LAWS))
    args = ap.parse_args()
    cfg = LAWS[args.law]

    doc = pymupdf.open(raw_pdf_path(cfg))
    records = parse_records(doc)
    chunks = records_to_chunks(records, cfg, get_settings().max_chunk_tokens)
    out = processed_dir(cfg)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "chunks.jsonl").open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(c.model_dump_json() + "\n")
    log.info(
        "%d records → %d chunks (%d sections) → %s",
        len(records),
        len(chunks),
        len({c.section for c in chunks}),
        out,
    )


if __name__ == "__main__":
    main()
