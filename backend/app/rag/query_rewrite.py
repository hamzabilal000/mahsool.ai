"""Query understanding: language, tax year, glossary hints and an English rewrite.

Search works best when the query uses the words the law uses. Users write "non filer hun, bank
se cash nikalwaun to kitna tax katega?"; the Ordinance says "advance tax on cash withdrawal ...
persons not appearing in the active taxpayers' list". A small LLM (GPT OSS 20B on Groq)
rewrites the question into 1-3 English legal search queries; the Urdu glossary tells it what
colloquial words mean in tax law.

Language and tax year are detected with rules first (cheap, predictable); the LLM only
fills gaps.
"""

import csv
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from backend.app.llm import ChatModel

Language = Literal["en", "ur", "roman_ur"]
Scope = Literal["income_tax", "other_federal_tax", "provincial_tax", "not_tax"]

URDU_CHAR_RE = re.compile(r"[؀-ۿݐ-ݿﭐ-﷿ﹰ-﻿]")
LATIN_CHAR_RE = re.compile(r"[A-Za-z]")
WORD_RE = re.compile(r"[a-z']+")

# Common Roman Urdu function words that are not also common English words.
_MARKER_WORDS = """
hai hain hay hun hoon hon ho ka ki ke ko se mein mai mujhe mera meri mere hamara humein
kya kia kitna kitni kitne kaise kese kaisay kab kahan kyun kyon aur ya nahi nahin nai bhi pe
wala wali walay walon agar tou hota hoti hotay hoga hogi hongay karna karta karti karte krna
kar kr raha rahi rahe tha thi thay apna apni apne liye lye sirf lekin magar jab jo jis jin
un unka iska uska kaun kon koi kuch sakta sakti saktay chahiye chahye parega padega lagta
lagega katega katay kata milega milta dena lena diya liya
"""
ROMAN_URDU_MARKERS = frozenset(_MARKER_WORDS.split())

TAX_YEAR_RES = [
    re.compile(r"\b(?:tax\s*year|ty|tax\s*sa+l)\s*[-:]?\s*(20\d\d)\b", re.IGNORECASE),
    re.compile(r"ٹیکس\s*سال\s*(20\d\d)"),
    re.compile(r"\b(20\d\d)\s*[-–/]\s*(\d\d)\b"),  # 2024-25 -> tax year 2025
]
URDU_DIGITS = str.maketrans("۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩", "01234567890123456789")


def detect_language(text: str) -> Language:
    urdu = len(URDU_CHAR_RE.findall(text))
    latin = len(LATIN_CHAR_RE.findall(text))
    if urdu and urdu >= latin:
        return "ur"
    words = WORD_RE.findall(text.lower())
    markers = sum(w in ROMAN_URDU_MARKERS for w in words)
    if markers >= 2 or (words and markers / len(words) >= 0.2):
        return "roman_ur"
    return "en"


def extract_tax_year(text: str) -> int | None:
    text = text.translate(URDU_DIGITS)
    for i, pattern in enumerate(TAX_YEAR_RES):
        m = pattern.search(text)
        if m:
            if i == 2:
                start, end = int(m.group(1)), int(m.group(2))
                if end != (start + 1) % 100:
                    continue
                return start + 1
            return int(m.group(1))
    return None


@dataclass(frozen=True)
class GlossaryEntry:
    roman: tuple[str, ...]
    urdu: tuple[str, ...]
    english: str
    section_ids: tuple[str, ...]
    notes: str = ""


def _urdu_in(term: str, text: str) -> bool:
    """Urdu term at the start of a word: "دن" (days) must not match inside "آمدن" (income)."""
    start = text.find(term)
    while start != -1:
        if start == 0 or not URDU_CHAR_RE.match(text[start - 1]):
            return True
        start = text.find(term, start + 1)
    return False


def _term_re(term: str) -> str:
    """Roman Urdu words inflect ("khareed" -> "khareedna", "khareedni", "khareedne"), so terms
    of 5+ letters also match up to 3 extra letters. Short terms must match exactly."""
    return re.escape(term) + (r"[a-z]{0,3}" if len(term) >= 5 and term[-1].isalpha() else "")


class Glossary:
    def __init__(self, entries: list[GlossaryEntry]) -> None:
        self.entries = entries
        self._patterns = [
            (e, re.compile(r"(?<![a-z])(?:" + "|".join(map(_term_re, e.roman)) + r")(?![a-z])"))
            if e.roman
            else (e, None)
            for e in entries
        ]

    @classmethod
    def load(cls, path: Path) -> "Glossary":
        with path.open(encoding="utf-8") as fh:
            rows = list(csv.DictReader(fh))
        split = lambda s: tuple(t.strip() for t in s.split("|") if t.strip())  # noqa: E731
        return cls(
            [
                GlossaryEntry(
                    roman=split(r["roman"].lower()),
                    urdu=split(r["urdu"]),
                    english=r["english"].strip(),
                    section_ids=tuple(r["section_ids"].split()),
                    notes=(r.get("notes") or "").strip(),
                )
                for r in rows
            ]
        )

    def match(self, question: str, limit: int = 15) -> list[tuple[str, GlossaryEntry]]:
        """Glossary entries whose Roman Urdu or Urdu spelling appears in the question."""
        low = question.lower()
        found: list[tuple[str, GlossaryEntry]] = []
        for entry, pattern in self._patterns:
            term = None
            if pattern and (m := pattern.search(low)):
                term = m.group(0)
            else:
                term = next((u for u in entry.urdu if _urdu_in(u, question)), None)
            if term:
                found.append((term, entry))
        # Longer (more specific) matches first: "non filer" before "filer".
        found.sort(key=lambda te: -len(te[0]))
        return found[:limit]


@dataclass
class QueryPlan:
    question: str
    language: Language
    tax_year: int
    tax_year_assumed: bool
    queries: list[str] = field(default_factory=list)  # English rewrites (without the original)
    scope: Scope = "income_tax"
    glossary_terms: list[str] = field(default_factory=list)


REWRITE_SYSTEM = """You turn a user's question about Pakistani tax into search queries for a \
search engine over the English text of the Income Tax Ordinance 2001, the Income Tax Rules 2002 \
and FBR's withholding tax rate card.

The question may be in English, Urdu script or Roman Urdu. Do NOT answer it.
Return JSON only:
{"queries": [1 to 3 English search queries], "tax_year": integer or null, "scope": one of \
"income_tax", "other_federal_tax", "provincial_tax", "not_tax"}

Rules for queries:
- Use the formal terms of the Ordinance (e.g. "deduction of tax at source from salary", \
"advance tax on purchase of immovable property", "persons not appearing in the active \
taxpayers' list", "return of income", "tax credit").
- The first query restates the whole question; the others cover a second angle (the rate, a \
condition, the related procedure) only if useful. Each under 25 words.
- Never add a section or rule number the user did not write; a wrong number misleads the \
search. Keep the numbers the user did write.
- Convert amounts to rupees: 1 lakh = Rs. 100,000, 1 crore = Rs. 10 million.
tax_year: only if the user states one (tax year 2025, 2024-25 -> 2025); otherwise null.
scope: decide from what the user asks about, not from single words (a glossary hint does not \
make a question income tax).
- "income_tax": federal income tax, withholding / advance tax (including tax deducted by banks, \
utilities or on property), filers and non-filers, the active taxpayers' list, NTN, returns and \
wealth statements.
- "other_federal_tax": sales tax on goods, federal excise, customs duty or PCT codes.
- "provincial_tax": provincial taxes (PRA, SRB, KPRA, BRA, sales tax on services, property tax, \
stamp duty, registration of property).
- "not_tax": anything else (investment advice, weather, general chat)."""


def rewrite_messages(question: str, hints: list[tuple[str, GlossaryEntry]]) -> list[dict]:
    user = f"Question: {question}"
    if hints:
        lines = []
        for term, e in hints:
            refs = ", ".join(s.split("-", 1)[1] for s in e.section_ids)
            lines.append(f'- "{term}" = {e.english}' + (f" (see {refs})" if refs else ""))
        user += "\n\nGlossary of the user's words (Urdu / Roman Urdu -> legal English):\n"
        user += "\n".join(lines)
    return [{"role": "system", "content": REWRITE_SYSTEM}, {"role": "user", "content": user}]


class QueryRewriter:
    def __init__(
        self,
        llm: ChatModel | None,
        model: str,
        glossary: Glossary | None = None,
        current_tax_year: int = 2027,
    ) -> None:
        self.llm, self.model, self.glossary = llm, model, glossary
        self.current_tax_year = current_tax_year

    def plan(self, question: str, *, rewrite: bool = True, use_glossary: bool = True) -> QueryPlan:
        rule_year = extract_tax_year(question)
        plan = QueryPlan(
            question=question,
            language=detect_language(question),
            tax_year=rule_year or self.current_tax_year,
            tax_year_assumed=rule_year is None,
        )
        if not rewrite or self.llm is None:
            return plan
        hints = self.glossary.match(question) if self.glossary and use_glossary else []
        plan.glossary_terms = [t for t, _ in hints]
        out = self.llm.chat_json(self.model, rewrite_messages(question, hints), max_tokens=600)
        queries = out.get("queries") or []
        if isinstance(queries, str):
            queries = [queries]
        plan.queries = [q.strip() for q in queries if isinstance(q, str) and q.strip()][:3]
        if out.get("scope") in ("income_tax", "other_federal_tax", "provincial_tax", "not_tax"):
            plan.scope = out["scope"]
        llm_year = out.get("tax_year")
        # Trust the LLM's tax year only if that year is actually written in the question.
        if rule_year is None and isinstance(llm_year, int) and 2003 <= llm_year <= 2035:
            text = question.translate(URDU_DIGITS)
            if str(llm_year) in text or f"{llm_year - 1}-{str(llm_year)[2:]}" in text:
                plan.tax_year, plan.tax_year_assumed = llm_year, False
        return plan
