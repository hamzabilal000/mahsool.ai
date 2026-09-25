"""Citation check: the answer may only cite sources that were actually retrieved.

The answer model sees sources numbered [1]..[n] and must end every sentence with one of those
numbers. Code (not the model) then verifies the citations:

- markers outside 1..n are removed from the text (the model invented a source);
- if no valid citation is left, the answer is refused rather than shown uncited;
- sentences without any marker, and section numbers the answer mentions that are not among
  the cited sources, are reported as warnings.
"""

import re
from dataclasses import dataclass, field

MARKER_RE = re.compile(r"\[(\d+(?:\s*,\s*\d+)*)\]")
SECTION_MENTION_RE = re.compile(r"\bsection\s+(\d{1,3}[A-Z]{0,3})\b", re.IGNORECASE)
SENTENCE_END_RE = re.compile(r"(?<=[.!?۔؟])\s+")


@dataclass
class CitationCheck:
    text: str  # answer with invalid markers removed
    cited: list[int]  # valid source numbers, in order of first use
    invalid: list[int] = field(default_factory=list)
    uncited_sentences: int = 0
    unsupported_sections: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return bool(self.cited)


def check_citations(
    answer: str, n_sources: int, declared: list[int] | None = None, source_sections: list[str] = ()
) -> CitationCheck:
    """`source_sections[i]` is the section number of source i+1 (e.g. "149"), for mentions."""
    cited: list[int] = []
    invalid: list[int] = []

    def fix(m: re.Match) -> str:
        nums = [int(x) for x in m.group(1).split(",")]
        good = [n for n in nums if 1 <= n <= n_sources]
        invalid.extend(n for n in nums if not 1 <= n <= n_sources)
        for n in good:
            if n not in cited:
                cited.append(n)
        return "[" + ", ".join(map(str, good)) + "]" if good else ""

    text = MARKER_RE.sub(fix, answer)
    text = re.sub(r"\s+([.,;:۔])", r"\1", text).strip()
    # Citations the model declared in JSON but never placed in the text still count if valid.
    for n in declared or []:
        if isinstance(n, int) and 1 <= n <= n_sources and n not in cited:
            cited.append(n)

    sentences = [s for s in SENTENCE_END_RE.split(text) if len(s.strip()) > 20]
    uncited = sum(1 for s in sentences if not MARKER_RE.search(s))

    cited_sections = {source_sections[n - 1].upper() for n in cited if n <= len(source_sections)}
    mentioned = [m.upper() for m in SECTION_MENTION_RE.findall(text)]
    unsupported = [m for m in dict.fromkeys(mentioned) if m not in cited_sections]
    return CitationCheck(
        text=text,
        cited=cited,
        invalid=invalid,
        uncited_sentences=uncited,
        unsupported_sections=unsupported,
    )
