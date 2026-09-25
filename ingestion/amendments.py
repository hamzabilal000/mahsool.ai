"""Turn FBR amendment footnotes into structured `amended_by` metadata."""

import re

# Footnotes often quote the repealed text after "read as follows". Laws named inside that
# quote are history of the *old* text, so only the part before it is searched.
_QUOTE_SPLIT_RE = re.compile(r"read\s+as\s+(?:follows|under)|reads?\s+as\s+follows", re.I)

_LAW_RE = re.compile(
    r"\b(?P<name>(?:Finance|Tax\s+Laws?|Income\s+Tax)(?:\s+Supplementary)?"
    r"(?:\s*\((?:[A-Za-z]+\s+)?(?:Amendment|Supplementary)\)){0,2})"
    r"\s*(?P<kind>Act|Ordinance)?,?\s*(?P<year>(?:19|20)\d{2})\b",
    re.I,
)
# "S.R.O. 389(I)/2009", "SRO 516(I)/2006", "S.R.O.428(1)/2002" (FBR sometimes types 1 for I)
_SRO_RE = re.compile(
    r"S\.?\s*R\.?\s*O\.?\s*(?:No\.?\s*)?(?P<no>\d+)\s*\(\s*[I1l]\s*\)\s*/\s*(?P<year>\d{4})",
    re.I,
)
_PRESIDENTIAL_RE = re.compile(r"Presidential\s+Order(?:\s+No\.?\s*(?P<no>[\w.()/-]+))?", re.I)


def _normalise(name: str, kind: str | None, year: str) -> str:
    name = re.sub(r"\s+", " ", name).strip()
    name = re.sub(r"\s*\(\s*", " (", name).replace(" )", ")")
    name = re.sub(r"\((\w)", lambda m: "(" + m.group(1).upper(), name)
    name = re.sub(r"\bamendment\b", "Amendment", name, flags=re.I)
    name = re.sub(r"^Tax Law\b(?!s)", "Tax Laws", name, flags=re.I)
    name = name[0].upper() + name[1:]
    return f"{name} {kind.capitalize()}, {year}" if kind else f"{name}, {year}"


def laws_in_footnote(text: str) -> list[str]:
    """Return the amending laws named in one footnote, e.g. ['Finance Act, 2025']."""
    head = _QUOTE_SPLIT_RE.split(text, maxsplit=1)[0]
    found: list[str] = []
    for m in _LAW_RE.finditer(head):
        name, kind = m.group("name"), m.group("kind")
        # "Income Tax Ordinance, 2001" is the law itself, not an amending law.
        if "(" not in name and (kind is None or not name.lower().startswith("finance")):
            continue
        law = _normalise(name, kind, m.group("year"))
        if law not in found:
            found.append(law)
    for m in _SRO_RE.finditer(head):
        law = f"SRO {m.group('no')}(I)/{m.group('year')}"
        if law not in found:
            found.append(law)
    for m in _PRESIDENTIAL_RE.finditer(head):
        law = "Presidential Order" + (f" No. {m.group('no')}" if m.group("no") else "")
        if law not in found:
            found.append(law)
    return found


def note_summary(text: str, limit: int = 300) -> str:
    """Short amendment note without the quoted old text."""
    head = _QUOTE_SPLIT_RE.split(text, maxsplit=1)[0].strip().rstrip(":-–— ")
    return head if len(head) <= limit else head[: limit - 1].rstrip() + "…"


def _year(law: str) -> int:
    m = re.search(r"(\d{4})$", law)
    return int(m.group(1)) if m else 0


def sort_laws(laws: set[str] | list[str]) -> list[str]:
    """Newest amendment first — that is the one users usually care about."""
    return sorted(set(laws), key=lambda law: (-_year(law), law))
