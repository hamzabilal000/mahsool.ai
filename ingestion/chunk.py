"""Section-aware chunker: parsed pages → one JSON chunk per section / schedule clause.

Chunks follow the law's own structure, never fixed-size windows:
  * Chapters: one chunk per section. Sections longer than `max_chunk_tokens` are split at
    sub-section boundaries ("(1)", "(2)", ...), and every piece after the first repeats
    the section number and title so it still makes sense on its own.
  * Second Schedule: one chunk per exemption clause.
  * Other schedules: one chunk per Part / Division, split by size; every rate table is its
    own chunk (markdown) with the sentence that introduces it as a caption.

Usage:
    python -m ingestion.chunk --law ITO2001
"""

import argparse
import json
import logging
import math
import re
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

from ingestion.amendments import laws_in_footnote, note_summary, sort_laws
from ingestion.laws import LAWS, LawConfig
from ingestion.models import Chunk, Footnote, Line, ParsedPage
from ingestion.parse import interim_path, toc_path
from ingestion.settings import get_settings
from ingestion.tax_year import tax_year_in_force

log = logging.getLogger(__name__)

# "149. Salary.—", "[5AA. Tax on ...", and FBR's occasional "[230E Directorate ..." (no dot).
SECTION_RE = re.compile(
    r"^\[*\s*(?P<num>\d{1,3}[A-Z]{0,4})\s*(?:[.\]]\s*|\s+(?=[A-Z]))(?P<rest>.*)$"
)
SUBSECTION_RE = re.compile(r"^\[*\s*\((?P<num>\d{1,3}[A-Z]{0,4})\)")
PARA_START_RE = re.compile(
    r"^\[*\s*(?:\((?:\d{1,3}[A-Z]{0,4}|[a-z]{1,2}[a-z]?|[ivxl]{1,6})\)|Provided|Explanation|Illustration)"
)
CHAPTER_RE = re.compile(r"^\[*\s*CHAPTER\s*[-–]?\s*[IVXL]+[A-Z]?\s*\]?$", re.I)
PART_RE = re.compile(r"^\[*\s*PART\s*[-–]?\s*(?P<num>[IVXL]+[A-Z]?)\s*\]?$", re.I)
DIVISION_RE = re.compile(
    r"^\[*\s*Division\s+(?P<num>[IVXL]+[A-Z]{0,2})\b\s*\]?\s*(?P<rest>.*)$", re.I
)
HEADER_PART_RE = re.compile(r"Part\s*[-–]?\s*(?P<num>[IVXL]+[A-Z]?)\b")
TITLE_END_RE = re.compile(r"\.?\s*[—―]|\.\s*[-–]|\s[-–]\s")
# "[ ]" marks omitted text; "[ ### ]", "[ %% ]" are placeholders for omitted entries.
EMPTY_BRACKETS_RE = re.compile(r"\[[\s#*%]*\]")
WS_RE = re.compile(r"[ \t]+")

ORDINALS = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "sixth": 6,
    "seventh": 7,
    "eighth": 8,
    "ninth": 9,
    "tenth": 10,
    "eleventh": 11,
    "twelfth": 12,
    "thirteenth": 13,
    "fourteenth": 14,
    "fifteenth": 15,
}


SMALL_WORDS = {"a", "an", "and", "at", "by", "for", "from", "in", "of", "on", "or", "the", "to"}


def heading_case(text: str) -> str:
    """'HEAD OF INCOME' → 'Head of Income', 'TAXPAYER’S' → 'Taxpayer’s' (unlike str.title)."""
    words = text.split()
    out = []
    for i, w in enumerate(words):
        low = w.lower()
        out.append(low if i and low in SMALL_WORDS else low[:1].upper() + low[1:])
    return " ".join(out)


def estimate_tokens(text: str) -> int:
    """~4 characters per token for English legal text (BGE-M3 / XLM-R tokenizer ballpark)."""
    return math.ceil(len(text) / 4)


def section_key(num: str) -> tuple[int, str]:
    m = re.match(r"(\d+)([A-Z]*)", num)
    return (int(m.group(1)), m.group(2)) if m else (0, num)


def clean_text(text: str) -> str:
    return WS_RE.sub(" ", EMPTY_BRACKETS_RE.sub("", text)).strip()


@dataclass
class Para:
    text: str
    pages: set[int]
    fn_keys: set[tuple[int, str]] = field(default_factory=set)
    is_table: bool = False

    @property
    def tokens(self) -> int:
        return estimate_tokens(self.text)


def lines_to_paras(lines: list[Line]) -> list[Para]:
    """Join wrapped lines into paragraphs; enumerators and provisos start a new one."""
    paras: list[Para] = []
    for ln in lines:
        keys = {(ln.page, m) for m in ln.fn_refs}
        if ln.kind == "table":
            if paras and paras[-1].is_table and ln.page == max(paras[-1].pages) + 1:
                # The same table continued on the next page: append its rows.
                prev, rows = paras[-1], ln.text.split("\n")
                first = rows[0]
                body = rows[2:] if first == prev.text.split("\n")[0] else [first, *rows[2:]]
                prev.text = "\n".join([prev.text, *body])
                prev.pages.add(ln.page)
                prev.fn_keys |= keys
                continue
            paras.append(Para(ln.text, {ln.page}, keys, is_table=True))
            continue
        text = ln.text
        if not paras or paras[-1].is_table or PARA_START_RE.match(text):
            paras.append(Para(text, {ln.page}, keys))
            continue
        prev = paras[-1]
        joiner = "" if prev.text.endswith("-") and text[:1].islower() else " "
        prev.text = f"{prev.text}{joiner}{text}"
        prev.pages.add(ln.page)
        prev.fn_keys |= keys
    for p in paras:
        if not p.is_table:
            p.text = clean_text(p.text)
    return [p for p in paras if p.text]


def extract_title(heading_text: str) -> str:
    """'149. Salary.—(1) Every employer...' → 'Salary'."""
    m = SECTION_RE.match(heading_text)
    rest = m.group("rest") if m else heading_text
    rest = rest.lstrip("[ ")
    end = TITLE_END_RE.search(rest[:300])
    title = rest[: end.start()] if end else " ".join(rest.split()[:10])
    title = re.sub(r"[\[\]]", "", title).strip().rstrip(".:;,")
    return title[:150]


def _split_long_para(p: Para, max_tokens: int) -> list[Para]:
    pieces: list[Para] = []
    buf = ""
    for sentence in re.split(r"(?<=[;.:])\s+", p.text):
        if buf and estimate_tokens(buf + " " + sentence) > max_tokens:
            pieces.append(Para(buf, set(p.pages), set(p.fn_keys)))
            buf = sentence
        else:
            buf = f"{buf} {sentence}".strip()
    if buf:
        pieces.append(Para(buf, set(p.pages), set(p.fn_keys)))
    return pieces


def split_table(p: Para, max_tokens: int) -> list[Para]:
    """Split a long markdown table by rows, repeating the header rows in every piece."""
    rows = p.text.split("\n")
    head, body = rows[:2], rows[2:]
    pieces: list[Para] = []
    buf: list[str] = []
    for row in body:
        if buf and estimate_tokens("\n".join(head + buf + [row])) > max_tokens:
            pieces.append(Para("\n".join(head + buf), set(p.pages), set(p.fn_keys), is_table=True))
            buf = []
        buf.append(row)
    if buf or not pieces:
        pieces.append(Para("\n".join(head + buf), set(p.pages), set(p.fn_keys), is_table=True))
    return pieces


def pack(paras: list[Para], max_tokens: int, budget_reserve: int = 30) -> list[list[Para]]:
    """Group paragraphs into pieces ≤ max_tokens, preferring sub-section boundaries."""
    limit = max_tokens - budget_reserve  # room for the repeated title line
    units: list[list[Para]] = []
    for p in paras:
        if not units or SUBSECTION_RE.match(p.text) or p.is_table:
            units.append([p])
        else:
            units[-1].append(p)

    atoms: list[list[Para]] = []
    for unit in units:
        if sum(p.tokens for p in unit) <= limit:
            atoms.append(unit)
            continue
        for p in unit:
            if p.tokens <= limit:
                atoms.append([p])
            elif p.is_table:
                atoms.extend([[q] for q in split_table(p, limit)])
            else:
                atoms.extend([[q] for q in _split_long_para(p, limit)])

    groups: list[list[Para]] = []
    current: list[Para] = []
    size = 0
    for atom in atoms:
        t = sum(p.tokens for p in atom)
        if current and size + t > limit:
            groups.append(current)
            current, size = [], 0
        current.extend(atom)
        size += t
    if current:
        groups.append(current)
    return groups


def subsection_label(group: list[Para], carried: str | None) -> tuple[str | None, str | None]:
    """Return (label for this piece, last sub-section seen) — e.g. ('(2)-(4)', '(4)')."""
    nums = [m.group("num") for p in group if (m := SUBSECTION_RE.match(p.text))]
    if not nums:
        return (f"({carried})" if carried else None), carried
    first = nums[0] if SUBSECTION_RE.match(group[0].text) or not carried else carried
    label = f"({first})" if first == nums[-1] else f"({first})-({nums[-1]})"
    return label, nums[-1]


@dataclass
class Unit:
    """A citable unit (section, schedule clause, schedule part) before it is split."""

    kind: str
    section_id: str
    title: str
    chapter: str | None = None
    part: str | None = None
    section: str | None = None
    schedule: str | None = None
    clause: str | None = None
    lines: list[Line] = field(default_factory=list)


class Chunker:
    def __init__(self, cfg: LawConfig, pages: list[ParsedPage], max_tokens: int) -> None:
        self.cfg = cfg
        self.pages = pages
        self.max_tokens = max_tokens
        self.tax_year_from = tax_year_in_force(cfg.version_date)
        self.footnotes: dict[tuple[int, str], list[Footnote]] = defaultdict(list)
        for page in pages:
            for fn in page.footnotes:
                self.footnotes[(page.page, fn.marker)].append(fn)
        self.body_re = re.compile(cfg.body_header_regex)
        self.schedule_re = re.compile(cfg.schedule_header_regex)
        self.end_re = re.compile(cfg.body_end_regex) if cfg.body_end_regex else None
        self.chunks: list[Chunk] = []
        self.skipped_headings: list[str] = []

    # ---------------------------------------------------------------- emit
    def _amendments(self, keys: set[tuple[int, str]]) -> tuple[list[str], list[str]]:
        laws: set[str] = set()
        notes: list[str] = []
        for key in sorted(keys):
            for fn in self.footnotes.get(key, []):
                laws.update(laws_in_footnote(fn.text))
                summary = note_summary(fn.text)
                if summary and summary not in notes:
                    notes.append(summary)
        return sort_laws(laws), notes

    def _make_chunk(
        self,
        unit: Unit,
        chunk_id: str,
        text: str,
        paras: list[Para],
        *,
        kind: str | None = None,
        subsection: str | None = None,
        needs_review: bool = False,
    ) -> Chunk:
        pages = sorted(set().union(*(p.pages for p in paras)))
        keys: set[tuple[int, str]] = set().union(*(p.fn_keys for p in paras))
        amended_by, notes = self._amendments(keys)
        return Chunk(
            chunk_id=chunk_id,
            section_id=unit.section_id,
            snapshot_id=self.cfg.snapshot_id,
            law=self.cfg.law,
            law_code=self.cfg.law_code,
            kind=kind or unit.kind,
            chapter=unit.chapter,
            part=unit.part,
            section=unit.section,
            subsection=subsection,
            schedule=unit.schedule,
            clause=unit.clause,
            title=unit.title,
            text=text,
            amended_by=amended_by,
            amendment_notes=notes,
            tax_year_from=self.tax_year_from,
            tax_year_to=None,
            source_url=self.cfg.source_url,
            page=pages[0],
            page_end=pages[-1],
            version_date=self.cfg.version_date,
            n_tokens=estimate_tokens(text),
            needs_review=needs_review,
        )

    def _continued_header(self, unit: Unit) -> str:
        if unit.kind == "section":
            return f"{self.cfg.unit_name} {unit.section}. {unit.title} (continued)"
        return f"{unit.title} (continued)"

    def flush(self, unit: Unit | None) -> None:
        if unit is None or not unit.lines:
            return
        paras = lines_to_paras(unit.lines)
        if not paras:
            return
        review = unit.kind != "section"

        text_paras = paras
        if unit.kind == "schedule_part":
            # Tables become their own chunks, captioned by the sentence that introduces them.
            text_paras = []
            n_tables = 0
            for i, p in enumerate(paras):
                if not p.is_table:
                    text_paras.append(p)
                    continue
                n_tables += 1
                context = [q for q in paras[max(0, i - 2) : i] if not q.is_table]
                caption = [q.text for q in context]
                budget = self.max_tokens - estimate_tokens("\n".join([unit.title, *caption])) - 10
                pieces = split_table(p, max(budget, 200))
                for j, piece in enumerate(pieces, start=1):
                    suffix = f"-t{n_tables}" if len(pieces) == 1 else f"-t{n_tables}-{j}"
                    body = "\n".join([unit.title, *caption, piece.text])
                    self.chunks.append(
                        self._make_chunk(
                            unit,
                            f"{unit.section_id}{suffix}",
                            body,
                            [piece, *context],
                            kind="table",
                            needs_review=True,
                        )
                    )
                text_paras.append(
                    Para(f"[Table {n_tables}: see {unit.section_id}-t{n_tables}]", set(p.pages))
                )
            if all(p.text.startswith("[Table ") for p in text_paras):
                return

        groups = pack(text_paras, self.max_tokens)
        carried: str | None = None
        for k, group in enumerate(groups, start=1):
            label, carried = subsection_label(group, carried)
            body = "\n".join(p.text for p in group)
            if k > 1:
                body = f"{self._continued_header(unit)}\n{body}"
            elif unit.kind == "schedule_part":
                body = f"{unit.title}\n{body}"
            chunk_id = unit.section_id if len(groups) == 1 else f"{unit.section_id}-{k}"
            self.chunks.append(
                self._make_chunk(
                    unit,
                    chunk_id,
                    body,
                    group,
                    subsection=label if unit.kind == "section" and len(groups) > 1 else None,
                    needs_review=review,
                )
            )

    # ------------------------------------------------------------- sections
    def _run_sections(self, pages: list[ParsedPage]) -> None:
        unit: Unit | None = None
        last_key = (0, "")
        # Structure state: "Part V: Advance Tax ...; Division III: Deduction Of Tax At Source".
        part: str | None = None
        division: str | None = None
        titles: dict[str, list[str]] = {"part": [], "division": []}
        collecting: str | None = None
        pending_heading: list[Line] = []
        chapter: str | None = None

        def structure() -> str | None:
            if not part:
                return None
            label = part + (f": {' — '.join(titles['part'])}" if titles["part"] else "")
            if division:
                label += f"; {division}" + (
                    f": {' — '.join(titles['division'])}" if titles["division"] else ""
                )
            return label

        for page in pages:
            if self.body_re.match(page.header):
                if page.header.strip() != chapter:
                    # A new chapter resets Part / Division tracking.
                    part, division, collecting = None, None, None
                    titles = {"part": [], "division": []}
                chapter = page.header.strip()
            for ln in page.lines:
                text = ln.text
                m = SECTION_RE.match(text) if ln.kind == "text" else None
                is_heading = (
                    m is not None
                    and ln.bold_start
                    and ln.x <= self.cfg.heading_max_x
                    and section_key(m.group("num")) > last_key
                )
                if m and ln.bold_start and ln.x <= self.cfg.heading_max_x and not is_heading:
                    self.skipped_headings.append(f"p{ln.page}: {text[:60]}")

                # Centred bold short lines are Part / Division titles, not section text.
                structural = (
                    ln.kind == "text"
                    and ln.bold_start
                    and ln.x > self.cfg.centered_min_x
                    and len(text) < 80
                    and not m
                    and not PARA_START_RE.match(text)
                )
                if structural or (
                    ln.kind == "text" and (CHAPTER_RE.match(text) or PART_RE.match(text))
                ):
                    dm = DIVISION_RE.match(text)
                    if CHAPTER_RE.match(text):
                        part, division, collecting = None, None, None
                        titles = {"part": [], "division": []}
                    elif pm := PART_RE.match(text):
                        part, division, collecting = f"Part {pm.group('num')}", None, "part"
                        titles = {"part": [], "division": []}
                    elif dm:
                        division, collecting = f"Division {dm.group('num').upper()}", "division"
                        titles["division"] = (
                            [heading_case(dm.group("rest").strip("[] "))]
                            if dm.group("rest").strip("[] ")
                            else []
                        )
                    elif collecting:
                        titles[collecting].append(heading_case(text.strip("[] ")))
                    continue

                if is_heading:
                    self.flush(unit)
                    collecting = None
                    num = m.group("num")
                    last_key = section_key(num)
                    unit = Unit(
                        kind="section",
                        section_id=f"{self.cfg.id_prefix}-{self.cfg.unit_code}{num}",
                        title="",
                        chapter=chapter,
                        part=structure(),
                        section=num,
                    )
                    pending_heading = []
                if unit is None:
                    continue  # preamble before section 1
                unit.lines.append(ln)
                if not unit.title:
                    pending_heading.append(ln)
                    joined = " ".join(x.text for x in pending_heading)
                    if TITLE_END_RE.search(joined) or len(pending_heading) >= 3:
                        unit.title = extract_title(joined)
            if unit and not unit.title and pending_heading:
                unit.title = extract_title(" ".join(x.text for x in pending_heading))
        self.flush(unit)

    # ------------------------------------------------------------ schedules
    def _schedule_of(self, header: str) -> tuple[str, int, str | None] | None:
        m = self.schedule_re.match(header)
        if not m or m.group("ordinal").lower() not in ORDINALS:
            return None
        n = ORDINALS[m.group("ordinal").lower()]
        pm = HEADER_PART_RE.search(header)
        return (
            f"{m.group('ordinal').title()} Schedule",
            n,
            (f"Part {pm.group('num')}" if pm else None),
        )

    def _run_schedules(self, pages: list[ParsedPage]) -> None:
        unit: Unit | None = None
        state: tuple[str, int, str | None] | None = None
        division: str | None = None
        last_clause = (0, "")
        prefix = self.cfg.id_prefix

        def new_block(name: str, n: int, part: str | None, div: str | None) -> Unit:
            sid = f"{prefix}-sch{n}"
            title = name
            if part:
                sid += f"-p{part.split()[-1]}"
                title += f", {part}"
            if div:
                sid += f"-div{div.split()[-1]}"
                title += f", {div}"
            return Unit(kind="schedule_part", section_id=sid, title=title, schedule=name, part=part)

        for page in pages:
            sched = self._schedule_of(page.header)
            if sched is None:
                continue
            if state is None or sched[:2] != state[:2] or (sched[2] and sched[2] != state[2]):
                self.flush(unit)
                division = None  # divisions are numbered afresh in every Part
                state, last_clause = sched, (0, "")
                unit = new_block(state[0], state[1], state[2], division)
            name, n, part = state

            for ln in page.lines:
                text = ln.text
                dm = DIVISION_RE.match(text) if ln.kind == "text" and ln.bold_start else None
                if dm and ln.x > 110 and f"Division {dm.group('num').upper()}" != division:
                    self.flush(unit)
                    division = f"Division {dm.group('num').upper()}"
                    unit = new_block(name, n, part, division)
                    unit.lines.append(ln)
                    continue

                cm = SUBSECTION_RE.match(text) if n == 2 and ln.kind == "text" else None
                if (
                    cm
                    and ln.bold_start
                    and ln.x <= self.cfg.heading_max_x
                    and section_key(cm.group("num")) > last_clause
                ):
                    self.flush(unit)
                    clause = cm.group("num")
                    last_clause = section_key(clause)
                    part_code = part.split()[-1] if part else "I"
                    words = " ".join(SUBSECTION_RE.sub("", text).split()[:12]).strip("[] ")
                    unit = Unit(
                        kind="schedule_clause",
                        section_id=f"{prefix}-sch2-p{part_code}-cl{clause}",
                        title=f"{name}, {part or 'Part I'}, clause ({clause}): {words}",
                        schedule=name,
                        part=part,
                        clause=f"({clause})",
                    )
                if unit is not None:
                    unit.lines.append(ln)
        self.flush(unit)

    # ----------------------------------------------------------------- run
    def run(self) -> list[Chunk]:
        # The body runs from the first chapter header to the first schedule page. Pages in
        # between whose running header is a continuation title still belong to the body.
        body: list[ParsedPage] = []
        schedules: list[ParsedPage] = []
        state = "front"
        for p in self.pages:
            if self._schedule_of(p.header) or (
                self.end_re is not None and self.end_re.match(p.header)
            ):
                state = "back"
            elif state == "front" and self.body_re.match(p.header):
                state = "body"
            if state == "body":
                body.append(p)
            elif state == "back" and self._schedule_of(p.header):
                schedules.append(p)
        if not self.cfg.include_schedules:
            schedules = []
        self._run_sections(body)
        self._run_schedules(schedules)
        return self.chunks


def load_toc(cfg: LawConfig) -> list[tuple[str, str]]:
    path = toc_path(cfg)
    if not path.exists():
        return []
    return [tuple(row) for row in json.loads(path.read_text(encoding="utf-8"))]


def is_live_toc_entry(title: str) -> bool:
    return not re.search(r"omitted|re-?numbered", title, re.I)


def build_report(chunks: list[Chunk], toc: list[tuple[str, str]], skipped: list[str]) -> dict:
    sections = {c.section for c in chunks if c.kind == "section"}
    live = [num for num, title in toc if is_live_toc_entry(title)]
    kinds: dict[str, int] = defaultdict(int)
    for c in chunks:
        kinds[c.kind] += 1
    return {
        "n_chunks": len(chunks),
        "by_kind": dict(kinds),
        "n_sections": len(sections),
        "toc_live_sections": len(live),
        "toc_live_missing": [n for n in live if n not in sections],
        "sections_not_in_toc": sorted(sections - {n for n, _ in toc}, key=section_key),
        "max_tokens_seen": max(c.n_tokens for c in chunks),
        "needs_review": sum(c.needs_review for c in chunks),
        "skipped_heading_candidates": skipped,
    }


def processed_dir(cfg: LawConfig) -> Path:
    return get_settings().processed_dir / cfg.id_prefix / cfg.version_date.isoformat()


def load_pages(cfg: LawConfig) -> list[ParsedPage]:
    with interim_path(cfg).open(encoding="utf-8") as fh:
        return [ParsedPage.model_validate_json(line) for line in fh]


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--law", default="ITO2001", choices=sorted(LAWS))
    args = ap.parse_args()
    cfg = LAWS[args.law]
    settings = get_settings()

    pages = load_pages(cfg)
    chunker = Chunker(cfg, pages, settings.max_chunk_tokens)
    chunks = chunker.run()
    report = build_report(chunks, load_toc(cfg), chunker.skipped_headings)

    out = processed_dir(cfg)
    out.mkdir(parents=True, exist_ok=True)
    with (out / "chunks.jsonl").open("w", encoding="utf-8") as fh:
        for c in chunks:
            fh.write(c.model_dump_json() + "\n")
    (out / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    log.info("wrote %d chunks to %s", len(chunks), out)
    log.info("report: %s", {k: v for k, v in report.items() if k != "skipped_heading_candidates"})


if __name__ == "__main__":
    main()
