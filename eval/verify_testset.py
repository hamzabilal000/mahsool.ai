"""Machine verification of the test set: two independent LLM judges plus a number check in code.

For every question, each judge reads ONLY the text of the gold section(s) and answers in JSON:
does the section answer the question, and does the reference answer match the section. Code then
checks that every number, percentage and amount in the reference answer appears in the gold text.
Both judges "yes" on both checks + all numbers found → "verified": "machine". Anything else is
written to eval/FLAGGED.md with the reasons.

- Out-of-scope questions have no gold text: the judges read the question and the list of laws
  Mahsool covers, and say whether it must be refused and whether the reference refusal is right.
- Urdu / Roman Urdu questions are translations of English ones with the same gold sections and
  reference answer. The judges check the English source once; a translation inherits the result
  only if a native speaker confirmed its wording ("language_ok": true).
- Long gold sections are cut to the chunks most related to the question (at most ~1,500 tokens
  per judge call, to stay inside Groq's free-tier limits); the number check always uses the
  whole section.

Judge outputs are cached in eval/cache/verify.jsonl, so a re-run only calls Groq for new or
changed questions; a run stopped by Groq's daily limit resumes where it stopped.

Usage:
    python -m eval.verify_testset              # verify, write eval/FLAGGED.md and the testset
    python -m eval.verify_testset --dry-run    # verify and report, don't touch testset.jsonl
"""

import argparse
import ast
import json
import re
from collections import defaultdict
from datetime import date
from pathlib import Path

from backend.app.config import get_settings
from backend.app.llm import GroqClient, LLMError
from backend.app.rag.corpus import load_chunks
from backend.app.rag.generator import source_label
from eval.run_eval import REPORTS
from eval.schema import TestItem
from eval.validate_testset import TESTSET, load_testset
from ingestion.models import Chunk

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "eval" / "cache" / "verify.jsonl"
FLAGGED = ROOT / "eval" / "FLAGGED.md"
# The plan named llama-3.3-70b-versatile as the second judge; Groq no longer serves it, so the
# second judge is Qwen, a different model family from GPT OSS (DECISIONS D38).
JUDGES = ("openai/gpt-oss-120b", "qwen/qwen3.8-27b")
# Qwen's free tier allows 1,000 output tokens a minute and counts its thinking, so it answers
# the yes/no check without thinking.
REASONING = {"openai/gpt-oss-120b": "low", "qwen/qwen3.8-27b": "none"}
MAX_EXCERPT_TOKENS = 1500

# --------------------------------------------------------------------------- number check

_UNITS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7,
    "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12, "thirteen": 13,
    "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17, "eighteen": 18,
    "nineteen": 19, "twenty": 20, "thirty": 30, "forty": 40, "fifty": 50, "sixty": 60,
    "seventy": 70, "eighty": 80, "ninety": 90,
}  # fmt: skip
_ORDINALS = {
    "first": 1, "second": 2, "third": 3, "fourth": 4, "fifth": 5, "sixth": 6, "seventh": 7,
    "eighth": 8, "ninth": 9, "tenth": 10, "eleventh": 11, "twelfth": 12, "fifteenth": 15,
    "twentieth": 20, "thirtieth": 30,
}  # fmt: skip
_SCALES = {"hundred": 100, "thousand": 1_000, "lakh": 100_000, "million": 1_000_000,
           "crore": 10_000_000, "billion": 1_000_000_000}  # fmt: skip
DIGITS_RE = re.compile(
    r"(?<!\w)(?<!\d\.)(\d{1,3}(?:,\d{2,3})+|\d+)(?:\.(\d+))?(?:\s*(lakh|million|crore|billion))?",
    re.I,
)
# Legal references are not quantities: "section 22 or 24", "clause (36) of section 2", "Part III".
LEGAL_REF_RE = re.compile(
    r"\b(?:u/s|sections?|sub-sections?|clauses?|sub-clauses?|rules?|sub-rules?|chapters?|"
    r"divisions?|paragraphs?|articles?|items?|serial)\s*(?:(?:\(?[0-9]+[A-Z]*\)?|\([a-z]+\))"
    r"(?:\s*(?:,|or|and|to|through|of)\s*)?)+"
    r"|\b(?:First|Second|Third|Fourth|Fifth|Sixth|Seventh|Eighth|Ninth|Tenth|Eleventh|Twelfth|"
    r"Thirteenth|Fourteenth|Fifteenth)\s+Schedule\b",
    re.I,
)
YEAR_RE = re.compile(r"\btax years?\s+(20\d\d)\b", re.I)
# "a% x b = Rs. c": a worked calculation in a reference answer.
EQUATION_RE = re.compile(r"([\d.,%xX×*/+\-−–()\s]|Rs\.?)+=\s*(?:Rs\.?\s*)?(\d[\d,]*(?:\.\d+)?)")


def _word_numbers(text: str, skip_lone_one: bool) -> set[float]:
    """ "one hundred and eighty-three" → 183, "ten million" → 10 and 10,000,000, "first" → 1."""
    values: set[float] = set()
    for segment in re.split(r"[;:,.()]", text.lower()):  # a number never spans punctuation
        values |= _segment_numbers(re.findall(r"[a-z]+", segment.replace("-", " ")), skip_lone_one)
    return values


def _segment_numbers(toks: list[str], skip_lone_one: bool) -> set[float]:
    values: set[float] = set()
    i = 0
    while i < len(toks):
        if toks[i] not in _UNITS and toks[i] not in _ORDINALS and toks[i] != "hundred":
            i += 1
            continue
        total, current, j = 0.0, 0.0, i
        while j < len(toks):
            w = toks[j]
            if w in _UNITS:
                current += _UNITS[w]
            elif w in _ORDINALS:
                if j > i and toks[j - 1] in _SCALES:
                    break  # "million first" is two numbers
                current += _ORDINALS[w]
                j += 1
                break
            elif w == "hundred":
                current = (current or 1) * 100  # "[hundred] million" = one hundred million
            elif w == "and" and toks[j + 1 : j + 3] == ["a", "half"]:
                current += 0.5  # "one and a half million"
                j += 3
                continue
            elif w in _SCALES:
                values.add(total + current)
                total, current = total + current * _SCALES[w], 0.0
            elif not (w == "and" and toks[j - 1] in _SCALES and j + 1 < len(toks)
                      and toks[j + 1] in _UNITS):  # fmt: skip
                break
            j += 1
        value = total + current
        if not (skip_lone_one and value == 1 and j == i + 1):  # "in one or more periods"
            values.add(value)
        i = j
    return values


def numbers_in(text: str, *, legal_refs: bool = True, skip_lone_one: bool = False) -> set[float]:
    """Every quantity in the text, as numbers: "Rs. 10 million", "ten million rupees",
    "10,000,000", "fifteen days", "0.8%"… Legal references are dropped when `legal_refs` is
    False (used for reference answers)."""
    text = text.replace("[", " ").replace("]", " ")  # amendment brackets: "[fifty]million"
    if not legal_refs:
        text = LEGAL_REF_RE.sub(" ", text)
    values: set[float] = set()
    for m in DIGITS_RE.finditer(text):
        v = float(m.group(1).replace(",", "") + (f".{m.group(2)}" if m.group(2) else ""))
        values.add(v)
        if m.group(3):
            values.add(v * _SCALES[m.group(3).lower()])
    return values | _word_numbers(text, skip_lone_one)


def _eval_arithmetic(expr: str) -> float | None:
    expr = re.sub(r"Rs\.?", "", expr).replace(",", "")
    expr = re.sub(r"(\d+(?:\.\d+)?)%", r"(\1/100)", expr)
    expr = re.sub(r"[xX×]", "*", expr).replace("−", "-").replace("–", "-")
    if not re.fullmatch(r"[\d.+\-*/()\s]+", expr) or not re.search(r"\d", expr):
        return None
    try:
        node = ast.parse(expr.strip(), mode="eval")
    except SyntaxError:
        return None
    allowed = (ast.Expression, ast.BinOp, ast.UnaryOp, ast.Constant, ast.Add, ast.Sub, ast.Mult,
               ast.Div, ast.USub)  # fmt: skip
    if not all(isinstance(n, allowed) for n in ast.walk(node)):
        return None
    try:
        return float(eval(compile(node, "<calc>", "eval")))  # only arithmetic nodes remain
    except ZeroDivisionError:
        return None


def missing_numbers(
    reference: str, gold_text: str, tax_year: int, question: str = ""
) -> list[float]:
    """Numbers in the reference answer found neither in the gold text nor in the question, and
    not the result of a calculation written out in the answer ("5% x 200,000 = Rs. 10,000")."""
    # "for tax year 2027" in a reference answer is the question's year, not a quantity from the law.
    ref = YEAR_RE.sub(lambda m: "" if int(m.group(1)) == tax_year else m.group(0), reference)
    have = numbers_in(gold_text) | numbers_in(question)
    for m in EQUATION_RE.finditer(ref):
        result = _eval_arithmetic(m.group(0).rsplit("=", 1)[0])
        rhs = float(m.group(2).replace(",", ""))
        if result is not None and abs(result - rhs) <= 0.5:
            have.add(rhs)
    wanted = numbers_in(ref, legal_refs=False, skip_lone_one=True)
    return sorted(v for v in wanted if not any(abs(v - h) < 1e-9 for h in have))


# --------------------------------------------------------------------------- gold excerpts


def _words(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]{4,}", text.lower())}


def gold_excerpt(item: TestItem, by_section: dict[str, list[Chunk]]) -> str:
    """Gold section text for the judges: whole sections if short, else the chunks sharing the
    most words with the question and reference answer, in document order."""
    chunks = [c for sid in item.gold_section_ids for c in by_section.get(sid, [])]
    if sum(c.n_tokens for c in chunks) > MAX_EXCERPT_TOKENS:
        target = _words(item.question + " " + item.reference_answer)
        ranked = sorted(chunks, key=lambda c: -len(target & _words(c.text)))
        keep, used = set(), 0
        for sid in item.gold_section_ids:  # at least the best chunk of every gold section
            best = next(c for c in ranked if c.section_id == sid)
            keep.add(best.chunk_id)
            used += best.n_tokens
        for c in ranked:
            if c.chunk_id not in keep and used + c.n_tokens <= MAX_EXCERPT_TOKENS:
                keep.add(c.chunk_id)
                used += c.n_tokens
        chunks = [c for c in chunks if c.chunk_id in keep]
    return "\n\n".join(f"[{source_label(c)}]\n{c.text}" for c in chunks)


# --------------------------------------------------------------------------- judges

JUDGE_SYSTEM = """You check questions in a test set for a Pakistani income tax assistant. You \
get a question, a reference answer and the text of the law section(s) that should answer it. \
Use ONLY the given section text, not your own knowledge of tax law.

Answer two questions:
1. section_answers_question: does the section text contain the answer to the question?
2. reference_matches_section: is everything the reference answer states supported by the \
section text (no wrong numbers, conditions or claims; leaving out minor details is fine)?

Return JSON only: {"section_answers_question": "yes" or "no", "reference_matches_section": \
"yes" or "no", "reason": "one or two short sentences"}"""

SCOPE_SYSTEM = """You check out-of-scope questions in a test set for an income tax assistant. \
The assistant covers ONLY: the Income Tax Ordinance 2001, the Income Tax Rules 2002 and FBR's \
withholding tax rate card for tax year 2027 (the current tax year). It must refuse questions \
about anything else (provincial taxes, sales tax, customs, other topics), questions about \
sections that do not exist in the Ordinance, future tax years whose law is not made yet, and \
requests that are not questions about the law.

Answer two questions:
1. section_answers_question: must the assistant refuse this question? ("yes" = refuse)
2. reference_matches_section: does the reference answer correctly say to refuse, for a correct \
reason?

Return JSON only: {"section_answers_question": "yes" or "no", "reference_matches_section": \
"yes" or "no", "reason": "one or two short sentences"}"""


def judge_messages(item: TestItem, excerpt: str) -> list[dict[str, str]]:
    if item.group == "out_of_scope":
        user = f"Question: {item.question}\n\nReference answer: {item.reference_answer}"
        return [{"role": "system", "content": SCOPE_SYSTEM}, {"role": "user", "content": user}]
    user = (
        f"Section text:\n{excerpt}\n\n---\nQuestion: {item.question}\n\n"
        f"Reference answer: {item.reference_answer}"
    )
    return [{"role": "system", "content": JUDGE_SYSTEM}, {"role": "user", "content": user}]


def yes(v) -> bool:
    return str(v).strip().lower() == "yes"


def verify(items: list[TestItem], llm: GroqClient) -> dict[str, dict]:
    """id → {"ok", "reasons", "judges", "missing_numbers", "inherited_from"}."""
    by_section: dict[str, list[Chunk]] = defaultdict(list)
    for c in load_chunks():
        by_section[c.section_id].append(c)
    results: dict[str, dict] = {}
    direct = [i for i in items if not i.source_id]
    for n, item in enumerate(direct, start=1):
        reasons, judges = [], {}
        excerpt = gold_excerpt(item, by_section) if item.group != "out_of_scope" else ""
        messages = judge_messages(item, excerpt)
        for model in JUDGES:
            try:
                out = llm.chat_json(
                    model, messages, max_tokens=700, reasoning_effort=REASONING[model]
                )
            except LLMError as e:
                judges[model] = {"error": str(e)[:200]}
                reasons.append(f"{model}: not run ({str(e)[:80]})")
                continue
            judges[model] = out
            checks = ("section_answers_question", "reference_matches_section")
            failed = [k for k in checks if not yes(out.get(k))]
            if failed:
                reasons.append(f"{model}: {', '.join(failed)} = no. {out.get('reason', '')}")
        missing: list[float] = []
        if item.group != "out_of_scope":
            full = "\n".join(c.text for sid in item.gold_section_ids for c in by_section[sid])
            missing = missing_numbers(item.reference_answer, full, item.tax_year, item.question)
            if missing:
                shown = ", ".join(f"{v:g}" for v in missing)
                reasons.append(f"numbers not in the gold text: {shown}")
        results[item.id] = {"ok": not reasons, "reasons": reasons, "judges": judges,
                            "missing_numbers": missing}  # fmt: skip
        print(f"{n}/{len(direct)} {item.id} {'ok' if not reasons else 'FLAGGED'}", flush=True)
    for item in items:
        if not item.source_id:
            continue
        src = results.get(item.source_id)
        reasons = [] if src and src["ok"] else [f"source question {item.source_id} is flagged"]
        if src is None:
            reasons = [f"source question {item.source_id} not verified"]
        if not item.language_ok:
            reasons.append("translation wording not checked by a native speaker yet")
        results[item.id] = {"ok": not reasons, "reasons": reasons, "judges": {},
                            "missing_numbers": [], "inherited_from": item.source_id}  # fmt: skip
    return results


def write_flagged(items: list[TestItem], results: dict[str, dict]) -> str:
    flagged = [i for i in items if not results[i.id]["ok"]]
    lines = [
        "# Flagged test-set questions",
        "",
        f"Generated by `python -m eval.verify_testset` on {date.today().isoformat()}. "
        f"{len(items) - len(flagged)} of {len(items)} questions passed "
        f"(judges: {', '.join(JUDGES)}; number check in code).",
        "",
    ]
    if not flagged:
        lines.append("Nothing is flagged.")
    else:
        lines += ["| id | split | question | reasons |", "|---|---|---|---|"]
        for i in flagged:
            q = i.question.replace("|", "/")
            q = q if len(q) <= 90 else q[:87] + "…"
            why = "<br>".join(r.replace("|", "/") for r in results[i.id]["reasons"])
            lines.append(f"| {i.id} | {i.split} | {q} | {why} |")
    FLAGGED.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return "\n".join(lines[:4])


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--dry-run", action="store_true", help="don't update testset.jsonl")
    args = ap.parse_args()

    settings = get_settings()
    key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else None
    llm = GroqClient(key, base_url=settings.groq_base_url, cache_path=CACHE)
    items = load_testset()
    results = verify(items, llm)

    REPORTS.mkdir(exist_ok=True)
    report = REPORTS / f"{date.today().isoformat()}-verify.json"
    report.write_text(json.dumps(results, indent=1, ensure_ascii=False), encoding="utf-8")
    print(write_flagged(items, results))
    if not args.dry_run:
        rows = [json.loads(line) for line in TESTSET.read_text(encoding="utf-8").splitlines()]
        for row in rows:
            if row.get("verified") != "human":
                row["verified"] = "machine" if results[row["id"]]["ok"] else False
        TESTSET.write_text(
            "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8"
        )


if __name__ == "__main__":
    main()
