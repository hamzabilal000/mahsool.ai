"""Parse an FBR consolidated-law PDF into clean body lines, footnotes and tables.

FBR PDFs are Word exports with a fixed layout:
  * a 12pt bold running header ("Chapter X – ...", "Second Schedule – Part-I") and a 12pt
    page number,
  * 10pt body text; amended text is wrapped as ``<superscript n>[new text]``,
  * footnotes under a 144pt-wide separator line at the left margin; they record amendments
    ("Inserted by the Finance Act, 2025") and often quote the *old* repealed text.

Old text in footnotes must never reach the index, or the assistant would quote repealed
law. So anything in the footnote zone is kept only as amendment metadata.

Usage:
    python -m ingestion.parse --law ITO2001
"""

import argparse
import json
import logging
import re
from collections import Counter
from itertools import pairwise
from pathlib import Path
from typing import Any

import pymupdf

from ingestion.laws import LAWS, LawConfig
from ingestion.models import Footnote, Line, ParsedPage
from ingestion.settings import get_settings

log = logging.getLogger(__name__)

MARKER_RE = re.compile(r"^(\d{1,3}|\*)$")
PRIVATE_USE_RE = re.compile(r"[-]")
WS_RE = re.compile(r"[ \t ]+")
PLAIN_FOOTNOTE_RE = re.compile(r"^(\d{1,3})\s+(\S.*)$")
EMPTY_BODY_RE = re.compile(r"^[\s\[\].;,*]*$")
INLINE_MARKER_IN_CELL_RE = re.compile(r"(?<![\w.,])\d{1,3}(?=\[)")

SUPERSCRIPT_RATIO = 0.9  # a span this much smaller than the line is a superscript
BASELINE_TOLERANCE = 3.0
SEPARATOR_WIDTH = (140.0, 150.0)


def _clean(text: str) -> str:
    return WS_RE.sub(" ", PRIVATE_USE_RE.sub("", text)).strip()


def _is_marker(span: dict[str, Any], dominant: float) -> bool:
    return (
        bool(MARKER_RE.match(span["text"].strip())) and span["size"] <= dominant * SUPERSCRIPT_RATIO
    )


def _dominant_size(spans: list[dict[str, Any]]) -> float:
    weights: Counter[float] = Counter()
    for s in spans:
        weights[round(s["size"], 1)] += len(s["text"].strip())
    return weights.most_common(1)[0][0] if weights else 10.0


class _RawLine:
    """Spans sharing one baseline, before marker handling."""

    def __init__(self, y: float, spans: list[dict[str, Any]]) -> None:
        self.y = y
        self.spans = spans

    @property
    def x(self) -> float:
        return min(s["bbox"][0] for s in self.spans)

    @property
    def top(self) -> float:
        return min(s["bbox"][1] for s in self.spans)

    def real_spans(self) -> list[dict[str, Any]]:
        return [s for s in self.spans if s["text"].strip()]


def _group_baselines(page: pymupdf.Page, junk_min_size: float) -> list[_RawLine]:
    """Merge PyMuPDF lines that share a baseline (e.g. '1.' and its title, justified words).

    Decorative glyphs (huge '..' marks) are dropped span-by-span first: they often share a
    baseline with a real heading, and dropping the whole merged line would lose the section.
    """
    items: list[tuple[float, float, list[dict[str, Any]]]] = []
    for block in page.get_text("dict")["blocks"]:
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"] and s["size"] < junk_min_size]
            if spans:
                items.append((line["bbox"][3], line["bbox"][0], spans))
    items.sort(key=lambda t: (t[0], t[1]))

    merged: list[_RawLine] = []
    for y, _x, spans in items:
        if merged and abs(merged[-1].y - y) <= BASELINE_TOLERANCE:
            merged[-1].spans.extend(spans)
        else:
            merged.append(_RawLine(y, list(spans)))
    for raw in merged:
        raw.spans.sort(key=lambda s: s["bbox"][0])
    return merged


def _assemble(raw: _RawLine) -> tuple[str, list[str], bool, bool, float]:
    """Return (text, fn_refs, bold_start, is_footnote_start, dominant_size)."""
    real = raw.real_spans()
    dominant = _dominant_size(real)
    refs: list[str] = []
    parts: list[str] = []
    prev_x1: float | None = None
    footnote_start = False
    bold_start = False
    seen_text = False

    for i, span in enumerate(real):
        text = span["text"]
        if _is_marker(span, dominant):
            marker = text.strip()
            nxt = real[i + 1]["text"].lstrip() if i + 1 < len(real) else ""
            if not seen_text and not parts and not nxt.startswith("["):
                footnote_start = True
            refs.append(marker)
            prev_x1 = span["bbox"][2]
            continue
        if not seen_text and any(ch.isalnum() for ch in text):
            # Inserted text starts with a plain '[' — judge boldness on the first real word.
            bold_start = bool(span["flags"] & 16)
            seen_text = True
        # Words split into separate spans on a justified line need a space between them.
        if prev_x1 is not None and span["bbox"][0] - prev_x1 > 1.5 and parts:
            parts.append(" ")
        parts.append(text)
        prev_x1 = span["bbox"][2]

    return _clean("".join(parts)), refs, bold_start, footnote_start, dominant


def _separator_y(page: pymupdf.Page, separator_x: float) -> float | None:
    ys = [
        d["rect"].y0
        for d in page.get_drawings()
        if d["rect"].height < 2
        and abs(d["rect"].x0 - separator_x) < 4
        and SEPARATOR_WIDTH[0] < d["rect"].width < SEPARATOR_WIDTH[1]
    ]
    return max(ys) if ys else None


def _has_ruling(page: pymupdf.Page) -> bool:
    """Cheap pre-check before the (slow) table finder: tables have many ruling lines."""
    return len(page.get_drawings()) >= 8


def _to_markdown(rows: list[list[str]]) -> str:
    width = max(len(r) for r in rows)
    rows = [[c.replace("|", "/") for c in r] + [""] * (width - len(r)) for r in rows]
    out = ["| " + " | ".join(rows[0]) + " |", "|" + "---|" * width]
    out += ["| " + " | ".join(r) + " |" for r in rows[1:]]
    return "\n".join(out)


def _table_markdown(rows: list[list[str | None]]) -> list[tuple[str | None, str]]:
    """Clean a table-finder grid into one or more (caption, markdown) tables.

    FBR tables confuse the table finder in three ways, all handled here:
      * merged cells leave empty or duplicated columns, and two stacked tables with
        different column offsets come back as one grid → rows are compacted to their
        non-empty cells;
      * the sentence introducing a table is swallowed as a one-cell row → it becomes the
        caption of the table that follows it;
      * a repeated header row means a second table starts → the grid is split there.
    """
    cleaned: list[list[str]] = []
    for row in rows:
        cells = []
        for cell in row:
            value = INLINE_MARKER_IN_CELL_RE.sub("", cell or "")
            cells.append(_clean(value.replace("\n", " ")))
        compact = [c for c in cells if c]
        if compact:
            cleaned.append(compact)

    tables: list[tuple[str | None, list[list[str]]]] = []
    caption: str | None = None
    current: list[list[str]] = []

    def close() -> None:
        nonlocal current, caption
        if len(current) >= 2 and max(len(r) for r in current) >= 2:
            tables.append((caption, current))
            caption = None
        elif current:
            caption = " ".join([caption or "", *(" ".join(r) for r in current)]).strip() or None
        current = []

    for row in cleaned:
        if len(row) == 1 and len(row[0]) > 60:
            close()
            caption = f"{caption} {row[0]}".strip() if caption else row[0]
            continue
        if current and row == current[0]:
            close()
        current.append(row)
    close()
    return [(cap, _to_markdown(grid)) for cap, grid in tables]


def parse_page(page: pymupdf.Page, cfg: LawConfig) -> ParsedPage:
    page_no = page.number + 1
    header_parts: list[str] = []
    printed: str | None = None
    body: list[tuple[_RawLine, Line, bool]] = []

    for raw in _group_baselines(page, cfg.junk_min_size):
        real = raw.real_spans()
        if not real:
            continue
        max_size = max(s["size"] for s in real)
        text = _clean("".join(s["text"] for s in real))
        if raw.top < cfg.header_max_y and max_size >= cfg.running_text_min_size:
            spaced = _clean(" ".join(s["text"] for s in real))
            header_parts.append(spaced.replace("_", "").strip())
            continue
        if raw.y > cfg.footer_min_y and max_size >= cfg.running_text_min_size:
            if text.strip().isdigit():
                printed = text.strip()
            continue
        line_text, refs, bold, fn_start, size = _assemble(raw)
        line = Line(
            page=page_no,
            y=round(raw.top, 1),
            x=round(raw.x, 1),
            text=line_text,
            bold_start=bold,
            size=size,
            fn_refs=refs,
        )
        body.append((raw, line, fn_start))

    sep = _separator_y(page, cfg.separator_x)
    tables = []
    if _has_ruling(page):
        tables = [t for t in page.find_tables().tables if t.row_count >= 2 and t.col_count >= 2]

    # Everything under the separator is footnote material. Footnotes that quote repealed
    # text often run over several pages; the carried-over part has no marker, so it is
    # stored with marker "" and joined to the previous page's last footnote in parse_pdf().
    zone_start = sep
    footnotes: list[Footnote] = []
    lines: list[Line] = []
    for _raw, line, fn_start in body:
        if zone_start is None or line.y < zone_start - 1:
            lines.append(line)
            continue
        # Some documents print the footnote number full-size instead of as a superscript.
        plain = PLAIN_FOOTNOTE_RE.match(line.text) if not fn_start else None
        if plain and abs(line.x - cfg.separator_x) < 6:
            footnotes.append(Footnote(page=page_no, marker=plain.group(1), text=plain.group(2)))
        elif fn_start and line.fn_refs:
            footnotes.append(Footnote(page=page_no, marker=line.fn_refs[0], text=line.text))
        elif footnotes:
            footnotes[-1].text = _clean(footnotes[-1].text + " " + line.text)
        else:
            footnotes.append(Footnote(page=page_no, marker="", text=line.text))

    # Tables: keep those above the footnote zone (tables inside footnotes are repealed text).
    for t in tables:
        if zone_start is not None and t.bbox[3] > zone_start + 5:
            continue  # starts in, or straddles into, the footnote zone
        parts = _table_markdown(t.extract())
        if not parts:
            continue
        top, bottom = t.bbox[1] - 1, t.bbox[3]
        lines = [ln for ln in lines if not (top <= ln.y <= bottom)]
        for i, (caption, md) in enumerate(parts):
            y = t.bbox[1] + i  # keep the pieces in order, captions just before their table
            if caption:
                lines.append(
                    Line(
                        page=page_no,
                        y=round(y - 0.5, 1),
                        x=round(t.bbox[0], 1),
                        text=caption,
                        bold_start=False,
                        size=0.0,
                    )
                )
            lines.append(
                Line(
                    page=page_no,
                    y=round(y, 1),
                    x=round(t.bbox[0], 1),
                    text=md,
                    bold_start=False,
                    size=0.0,
                    kind="table",
                )
            )

    lines = [ln for ln in lines if ln.kind == "table" or not EMPTY_BODY_RE.match(ln.text)]
    lines.sort(key=lambda ln: (ln.y, ln.x))
    return ParsedPage(
        page=page_no,
        header=" ".join(header_parts).strip(),
        printed_page=printed,
        lines=lines,
        footnotes=footnotes,
    )


def parse_pdf(pdf_path: Path, cfg: LawConfig) -> list[ParsedPage]:
    doc = pymupdf.open(pdf_path)
    pages = [parse_page(page, cfg) for page in doc]
    for prev, page in pairwise(pages):
        if page.footnotes and page.footnotes[0].marker == "" and prev.footnotes:
            carried = page.footnotes.pop(0)
            prev.footnotes[-1].text = _clean(f"{prev.footnotes[-1].text} {carried.text}")
    log.info("parsed %d pages from %s", len(pages), pdf_path.name)
    return pages


TOC_NUM_RE = re.compile(r"^(\d{1,3}[A-Z]{0,4})\s*\.?$")
TOC_PAGE_RE = re.compile(r"^\d{1,3}$")
TOC_STRUCTURE_RE = re.compile(r"^(?:CHAPTER|PART|Division)\b", re.I)
TOC_SCHEDULE_RE = re.compile(r"^(?:THE\s+)?[A-Z]+\s+SCHEDULE\b", re.I)


def extract_toc(doc: pymupdf.Document, cfg: LawConfig) -> list[tuple[str, str]]:
    """(section number, title) pairs from the table of contents before the body starts.

    Read from the raw text stream (number, title lines, page number), which is more robust
    than the table finder for this multi-page layout. Stops at the Schedules listing.
    """
    body_re = re.compile(cfg.body_header_regex)
    toc: list[tuple[str, str]] = []

    def is_number(line: str) -> bool:
        return bool(TOC_NUM_RE.match(line) or TOC_PAGE_RE.match(line))

    for page in doc:
        if body_re.match(parse_page_header(page, cfg)):
            break
        lines = [ln.strip() for ln in page.get_text().split("\n") if ln.strip()]
        for i, line in enumerate(lines[:-1]):
            m = TOC_NUM_RE.match(line)
            # An entry is a number followed by a text title (then, usually, a page number).
            if not m or is_number(lines[i + 1]) or TOC_STRUCTURE_RE.match(lines[i + 1]):
                continue
            title: list[str] = []
            for nxt in lines[i + 1 :]:
                if is_number(nxt) or TOC_STRUCTURE_RE.match(nxt):
                    break
                title.append(nxt)
            text = _clean(" ".join(title))
            if TOC_SCHEDULE_RE.match(text):
                return toc
            num = m.group(1).lstrip("0") or "0"
            last = int(re.match(r"\d+", toc[-1][0]).group()) if toc else 0
            if int(re.match(r"\d+", num).group()) <= last + 50:  # skip stray page numbers
                toc.append((num, text))
    return toc


def parse_page_header(page: pymupdf.Page, cfg: LawConfig) -> str:
    parts = []
    for raw in _group_baselines(page, cfg.junk_min_size):
        real = raw.real_spans()
        if (
            real
            and raw.top < cfg.header_max_y
            and max(s["size"] for s in real) >= cfg.running_text_min_size
        ):
            parts.append(_clean(" ".join(s["text"] for s in real)).replace("_", "").strip())
    return " ".join(parts)


def toc_path(cfg: LawConfig) -> Path:
    return get_settings().interim_dir / cfg.id_prefix / f"{cfg.version_date.isoformat()}.toc.json"


def raw_pdf_path(cfg: LawConfig) -> Path:
    return get_settings().raw_dir / cfg.id_prefix / f"{cfg.version_date.isoformat()}.pdf"


def interim_path(cfg: LawConfig) -> Path:
    name = f"{cfg.version_date.isoformat()}.pages.jsonl"
    return get_settings().interim_dir / cfg.id_prefix / name


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--law", default="ITO2001", choices=sorted(LAWS))
    args = ap.parse_args()
    cfg = LAWS[args.law]

    pdf = raw_pdf_path(cfg)
    pages = parse_pdf(pdf, cfg)
    toc = extract_toc(pymupdf.open(pdf), cfg)
    toc_path(cfg).parent.mkdir(parents=True, exist_ok=True)
    toc_path(cfg).write_text(json.dumps(toc, ensure_ascii=False, indent=1), encoding="utf-8")
    log.info("table of contents: %d entries", len(toc))
    out = interim_path(cfg)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as fh:
        for p in pages:
            fh.write(json.dumps(p.model_dump(), ensure_ascii=False) + "\n")
    log.info("wrote %s", out)


if __name__ == "__main__":
    main()
