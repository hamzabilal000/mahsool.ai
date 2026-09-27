"""Direct lookup: when a question names a section or rule, fetch it by id before searching.

"section 149", "sec. 236K", "u/s 4AB", "dafa 236k", "دفعہ 149" -> ITO2001-s149 ...
"rule 5", "qaida 5", "قاعدہ 5"                                   -> ITR2002-r5

A reference that doesn't exist (e.g. "section 999Z") returns nothing, so the question goes
through normal search and the answer step can say the section isn't in the law.
"""

import re
from dataclasses import dataclass

from ingestion.models import Chunk

URDU_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")

# A number with an optional letter suffix: 149, 236K, 4AB, 13P. The suffix must not run into
# a following word ("section 149salary" is not a thing, but "section 149 salary" is common).
_NUM = r"(\d{1,3}[A-Za-z]{0,3})(?![A-Za-z0-9])"
SECTION_RE = re.compile(
    rf"(?:\bsections?|\bsec\.?|\bs\.|\bu/s|\bdaf(?:a|ah|'a|aa)|دفعہ|دفعه)\s*(?:no\.?\s*)?{_NUM}",
    re.IGNORECASE,
)
RULE_RE = re.compile(
    rf"(?:\brules?|\bqa(?:a|e)?ida|\bqaeda|قاعدہ|قاعده|رول)\s*(?:no\.?\s*)?{_NUM}", re.IGNORECASE
)


@dataclass(frozen=True)
class Reference:
    section_id: str
    matched: str


def _normalise(num: str) -> str:
    digits = re.match(r"\d+", num)
    assert digits is not None
    return digits.group() + num[digits.end() :].upper()


class SectionLookup:
    def __init__(self, chunks: list[Chunk]) -> None:
        self.chunks_by_section: dict[str, list[Chunk]] = {}
        for c in chunks:
            self.chunks_by_section.setdefault(c.section_id, []).append(c)

    def find(self, question: str) -> list[Reference]:
        return self.resolve(question)[0]

    def resolve(self, question: str) -> tuple[list[Reference], list[str]]:
        """Referenced sections that exist, and references that don't ("section 999Z")."""
        text = question.translate(URDU_DIGITS)
        refs: list[Reference] = []
        missing: list[str] = []
        for pattern, prefix, label in (
            (SECTION_RE, "ITO2001-s", "section"),
            (RULE_RE, "ITR2002-r", "rule"),
        ):
            for m in pattern.finditer(text):
                num = _normalise(m.group(1))
                sid = prefix + num
                if sid in self.chunks_by_section:
                    if all(r.section_id != sid for r in refs):
                        refs.append(Reference(section_id=sid, matched=m.group(0)))
                elif f"{label} {num}" not in missing:
                    missing.append(f"{label} {num}")
        return refs, missing

    def chunk_ids(self, section_id: str) -> list[str]:
        return [c.chunk_id for c in self.chunks_by_section.get(section_id, [])]


# --------------------------------------------------------------------------- definitions (D57)

# A defined term in section 2: '(45) "private company" means', '[(59AB)] "Small Company"',
# '(54) [royalty] means'. The clause number is kept for the answer's citation.
_DEF_QUOTED = re.compile(r'\(\s*(\d+[A-Z]*)\s*\)\]?\s*\[?\s*[“"‘]([^”"’“]{2,80})[”"’]')
_DEF_BRACKETED = re.compile(
    r"\(\s*(\d+[A-Z]*)\s*\)\s*\[([a-z][^\]\[]{1,60})\]\s*(?:means|includes)"
)
# Definitional phrasings; the defined term must follow directly.
_DEF_TRIGGER = re.compile(
    r"\b(?:define[sd]?|definition\s+of|meaning\s+of|what\s+(?:is|are)|what\s+counts\s+as|"
    r"who\s+(?:is|are)|what\s+does)\s+(?:the\s+|an?\s+)?(?:term\s+)?",
    re.IGNORECASE,
)
# What may follow the term for the match to count: the end, or a word that closes the phrase.
# "what is the tax rate" must not pin the definition of "tax".
_DEF_AFTER = re.compile(
    r"\s*(?:$|[?.,;:!)\"'”’]|(?:for|under|in|as|according|mean|means|defined|include|includes)\b)",
    re.IGNORECASE,
)


# '"taxable income" means taxable income as defined in section 9': the definition only points
# elsewhere, so the section it points to is what answers the question.
_DEF_POINTER = re.compile(
    r"(?:defined|referred\s+to|specified|mentioned)\s+in\s+(?:sub-section\s*\(\w+\)\s+of\s+)?"
    r"section\s+(\d+[A-Z]*)",
    re.IGNORECASE,
)


def _clean_term(term: str) -> str:
    return re.sub(r"\s+", " ", term.replace("’", "'").replace("‘", "'")).strip(" '").lower()


class DefinitionLookup:
    """Pins the section 2 clause that defines a term when a question asks what the term means.

    Definitions live in one very long section, and search tends to find the sections that use a
    term rather than the clause that defines it ("what is imputable income?"). This is the same
    idea as the section lookup: a deterministic rule, no model."""

    def __init__(self, chunks: list[Chunk], section_id: str = "ITO2001-s2") -> None:
        self.terms: dict[str, tuple[str, str]] = {}  # term -> (clause, chunk_id)
        self.points_to: dict[str, str] = {}  # term -> section id, for pointer definitions
        prefix = section_id.rsplit("-s", 1)[0] + "-s"
        for c in chunks:
            if c.section_id != section_id:
                continue
            for pattern in (_DEF_QUOTED, _DEF_BRACKETED):
                for m in pattern.finditer(c.text):
                    term = _clean_term(m.group(2))
                    if term in self.terms:
                        continue
                    self.terms[term] = (m.group(1), c.chunk_id)
                    # The definition's own words: up to the end of the clause (";" or newline).
                    body = re.split(r";|\n", c.text[m.end() : m.end() + 300], maxsplit=1)[0]
                    target = _DEF_POINTER.search(body)
                    if target and len(body) < 160:
                        self.points_to[term] = prefix + target.group(1).upper()
        # Longest terms first, so "small and medium enterprise" wins over "enterprise".
        self._ordered = sorted(self.terms, key=len, reverse=True)

    def find(self, texts: list[str]) -> list[tuple[str, str, str]]:
        """(term, clause, chunk_id) for each definition asked for in any of the texts.
        Pointer definitions are left out; `targets()` gives the sections they point to."""
        return [f for f in self._find(texts) if f[0] not in self.points_to]

    def targets(self, texts: list[str]) -> list[str]:
        """Section ids that pointer definitions asked for in the texts point to."""
        return list(dict.fromkeys(self.points_to[f[0]] for f in self._find(texts)
                                  if f[0] in self.points_to))  # fmt: skip

    def _find(self, texts: list[str]) -> list[tuple[str, str, str]]:
        found: list[tuple[str, str, str]] = []
        for text in texts:
            for m in _DEF_TRIGGER.finditer(text):
                rest = text[m.end() :].lower().replace("’", "'")
                for term in self._ordered:
                    if rest.startswith(term) and _DEF_AFTER.match(rest[len(term) :]):
                        clause, chunk_id = self.terms[term]
                        if all(f[2] != chunk_id or f[0] != term for f in found):
                            found.append((term, clause, chunk_id))
                        break
        return found


# --------------------------------------------------------------------------- ATL rules (D63)

# "Division-IA, Part-III of First Schedule read with R.1 of Tenth Schedule", "R.10(a) of Tenth
# Schedule", "R.1, Tenth Schedule": the rate card's pointer to a Tenth Schedule rule.
_CARD_RULE = re.compile(r"\bR\.\s*(\d{1,2})\b[^|]{0,30}?Tenth Schedule", re.IGNORECASE)
# A rule's opening words inside the Tenth Schedule text: "1. Rate of deduction", "10. The
# provisions of this Schedule". Sub-clauses like "(1)" or "(a)" do not match.
_SCHEDULE_RULE = re.compile(r"(?:^|[\s\[])(\d{1,2})\.\s+\[?[A-Z]")
# The question is about filer / non-filer (ATL) status.
_ATL_QUESTION = re.compile(
    r"\b(?:non[\s-]?filers?|filers?|non[\s-]?atl|atl|active\s+tax\s*payers?'?s?\s+list)\b"
    r"|فائلر|ایکٹو\s*ٹیکس",
    re.IGNORECASE,
)
# Sections whose non-ATL rates are set by a table of the Tenth Schedule's rule 1 provisos.
_RULE1_TABLES = {"236K": "t1", "236C": "t2", "236G": "t2", "236H": "t2"}


class AtlRuleLookup:
    """Adds the Tenth Schedule rule a rate depends on, and the rate card for a filer question.

    The rate card shows ATL and non-ATL rates and points to "R.1 of Tenth Schedule" (rates double
    for persons not on the Active Taxpayers' List) or to a rule 10 exception. Without that rule
    among the sources, the answer model may say a rate applies "regardless of ATL status" (D63).
    These are companions: extra answer sources after the ranked ones, so retrieval ranks and
    Hit@5 do not change."""

    def __init__(self, chunks: list[Chunk], schedule_id: str = "ITO2001-sch10") -> None:
        self.rule_chunk: dict[int, str] = {}  # rule number -> chunk id where it starts
        self.tables: dict[str, str] = {}  # "t1" -> chunk id
        self.cards: dict[str, list[str]] = {}  # section number -> rate card chunk ids
        for c in chunks:
            if c.section_id == schedule_id:
                suffix = c.chunk_id.rsplit("-", 1)[1]
                if suffix.startswith("t"):
                    self.tables[suffix] = c.chunk_id
                    continue
                for m in _SCHEDULE_RULE.finditer(c.text):
                    n = int(m.group(1))
                    # Rules run 1, 2, ... 10: a number is a rule only if it is the next one.
                    if n == max(self.rule_chunk, default=0) + 1:
                        self.rule_chunk[n] = c.chunk_id
            elif c.law_code == "WHT" and c.section:
                self.cards.setdefault(c.section, []).append(c.chunk_id)

    @staticmethod
    def is_atl_question(texts: list[str]) -> bool:
        return any(_ATL_QUESTION.search(t) for t in texts)

    def companions(self, top: list[Chunk], texts: list[str], limit: int = 3) -> list[str]:
        """Chunk ids to add after the `top` answer sources (question + rewrites in `texts`)."""
        have = {c.chunk_id for c in top}
        rules: list[int] = []
        cards: list[str] = []
        sections = [c for c in top if c.law_code == "WHT"]
        if self.is_atl_question(texts):
            rules.append(1)
            # The rate card of the sections the top sources are about, for both rates.
            for c in top[:3]:
                if c.law_code == "ITO" and c.section and not c.schedule:
                    for cid in self.cards.get(c.section, [])[:1]:
                        cards.append(cid)
                        sections.append(c)
        for c in top:
            if c.law_code == "WHT":
                rules += [int(n) for n in _CARD_RULE.findall(c.text)]
        extra: list[str] = list(cards)
        for n in dict.fromkeys(rules):
            if n in self.rule_chunk:
                extra.append(self.rule_chunk[n])
        if 1 in rules:
            for c in sections:
                table = _RULE1_TABLES.get(c.section or "")
                if table in self.tables:
                    extra.append(self.tables[table])
        return [cid for cid in dict.fromkeys(extra) if cid not in have][:limit]
