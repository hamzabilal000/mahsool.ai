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
                rest = rest.lstrip("\"'“‘")  # a quoted term: what does "business" include (D69)
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
# "Division-V of Part-III of First Schedule", "Division IC of Part III of the First Schedule",
# "Division-I, Part-III": the rate division a rate-card row comes from.
_CARD_DIVISION = re.compile(
    r"Division[\s-]*([IVXl]+[A-C]*)\s*,?\s*(?:of\s+)?Part[\s-]*([IVX]+)\s+of\s+(?:the\s+)?First"
)
# A First Schedule division chunk: ITO2001-sch1-pIII-divV, ITO2001-sch1-pIII-divV-t1, ...-divX-2.
_DIVISION_ID = re.compile(r"^(ITO2001-sch1-p[IVX]+-div[IVXA-Z]+?)(?:-t?\d+)?$")
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
        self.division_card: dict[str, str] = {}  # First Schedule division id -> section number
        self.card_rules: dict[str, list[int]] = {}  # rate card chunk id -> Tenth Schedule rules
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
                self.card_rules[c.chunk_id] = card_rule_numbers(c.text)
                for div, part in _CARD_DIVISION.findall(c.text):
                    key = f"ITO2001-sch1-p{part}-div{div.replace('l', 'I')}"
                    self.division_card.setdefault(key, c.section)

    def card_section(self, chunk: Chunk) -> str | None:
        """The rate card section for an Ordinance section or a First Schedule rate division."""
        if chunk.law_code == "ITO" and chunk.section and not chunk.schedule:
            return chunk.section if chunk.section in self.cards else None
        m = _DIVISION_ID.match(chunk.chunk_id)
        return self.division_card.get(m.group(1)) if m else None

    @staticmethod
    def is_atl_question(texts: list[str]) -> bool:
        return any(_ATL_QUESTION.search(t) for t in texts)

    def companions(
        self, top: list[Chunk], texts: list[str], limit: int = 3, named: list[str] = ()
    ) -> list[str]:
        """Chunk ids to add after the `top` answer sources (question + rewrites in `texts`).

        1. The rate card of the section the best sources are about (top 3: an Ordinance section
           or its First Schedule rate division), when no card of that section is among them: it
           gives the ATL and non-ATL rates side by side.
        2. The Tenth Schedule rule each rate card among the top 3 points to (R.1: rates double
           for persons not on the ATL, with its tables for 236K / 236C / 236G / 236H; R.10: the
           sections where they do not), and rule 1 for any question about filer status.
        3. For a filer question, the rate card of the sections its glossary terms name (`named`,
           e.g. "bank munafa" -> ITO2001-s151), when search found neither the section nor its card
           ("bank munafa ... non filer", D63)."""
        have = {c.chunk_id for c in top}
        atl = self.is_atl_question(texts)
        cards: list[str] = []
        card_sections = {c.section for c in top if c.law_code == "WHT"}
        for c in top[:3]:
            section = self.card_section(c)
            if section and section not in card_sections:
                card = self.cards[section][0]
                # A card whose rates do not change with ATL status (rule 10 exceptions, e.g.
                # salary) is added only when the question is about filer status.
                if atl or 1 in self.card_rules.get(card, []):
                    card_sections.add(section)
                    cards.append(card)
        if atl and not card_sections:
            for sid in named:
                section = sid.rsplit("-s", 1)[-1]
                if sid.startswith("ITO2001-s") and section in self.cards:
                    card_sections.add(section)
                    cards.append(self.cards[section][0])
                    break
        rules = [1] if atl else []
        # Only the cards among the best 3 sources: a card further down is usually about another
        # payment, and its rule 1 would make the answer double a rate that does not double (D69).
        for c in top[:3]:
            if c.law_code == "WHT":
                rules += [n for n in card_rule_numbers(c.text) if n == 1 or atl]
        rules += [n for cid in cards for n in self.card_rules.get(cid, []) if n == 1 or atl]
        rule_ids = [self.rule_chunk[n] for n in dict.fromkeys(rules) if n in self.rule_chunk]
        tables = []
        if 1 in rules:
            for section in sorted(card_sections):
                table = _RULE1_TABLES.get(section)
                if table in self.tables:
                    tables.append(self.tables[table])
        # The first card, then the rules it depends on, then more cards and the tables.
        extra = [*cards[:1], *rule_ids, *cards[1:], *tables]
        return [cid for cid in dict.fromkeys(extra) if cid not in have][:limit]


def card_rule_numbers(text: str) -> list[int]:
    return [int(n) for n in _CARD_RULE.findall(text)]
