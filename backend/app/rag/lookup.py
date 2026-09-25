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
