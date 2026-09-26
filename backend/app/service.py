"""Answer a question end to end: search, guardrails, grounded answer, citation check.

Refusal happens at the first failed check, cheapest first, so most out-of-scope questions
never reach the answer model:

1. scope (from the rewrite step): provincial tax, customs, non-tax -> refuse
2. tax year: no law text loaded for that year, or a future year -> refuse
3. the question names only sections that don't exist ("section 999Z") -> refuse
4. best reranker score below the threshold -> refuse
5. the answer model says the sources don't answer it -> refuse
6. no valid citation left after the citation check -> refuse
"""

import time
from collections.abc import Callable

from backend.app.models.schemas import AskData, Citation, RefusalReason, Source
from backend.app.rag.citations import check_citations
from backend.app.rag.generator import AnswerGenerator, source_label
from backend.app.rag.pipeline import RAGPipeline, SearchResult
from backend.app.rag.query_rewrite import Language
from backend.app.timing import request_timer
from backend.app.timing import stage as timed

COVERAGE = "Income Tax Ordinance 2001, Income Tax Rules 2002 and the FBR withholding tax rate card"
REFUSAL = {
    "en": f"I couldn't find this in the tax laws I cover ({COVERAGE}).",
    "ur": "مجھے یہ بات اُن ٹیکس قوانین میں نہیں ملی جو میرے پاس ہیں (انکم ٹیکس آرڈیننس 2001، "
    "انکم ٹیکس رولز 2002 اور ایف بی آر کا ود ہولڈنگ ٹیکس ریٹ کارڈ)۔",
    "roman_ur": "Mujhe yeh baat un tax qawaneen mein nahi mili jo mere paas hain "
    "(Income Tax Ordinance 2001, Income Tax Rules 2002 aur FBR withholding tax rate card).",
}
TAX_YEAR_REFUSAL = {
    "en": "I only have the law for tax year {first} onwards, so I can't answer for tax year "
    "{year}.",
    "ur": "میرے پاس صرف ٹیکس سال {first} اور اس کے بعد کا قانون ہے، اس لیے ٹیکس سال {year} "
    "کا جواب نہیں دے سکتا۔",
    "roman_ur": "Mere paas sirf tax year {first} aur uske baad ka qanoon hai, is liye tax year "
    "{year} ka jawab nahi de sakta.",
}
FUTURE_TAX_YEAR_REFUSAL = {
    "en": "The law for tax year {year} has not been made yet; I have the law up to tax year "
    "{last}.",
    "ur": "ٹیکس سال {year} کا قانون ابھی بنا نہیں؛ میرے پاس ٹیکس سال {last} تک کا قانون ہے۔",
    "roman_ur": "Tax year {year} ka qanoon abhi bana nahi; mere paas tax year {last} tak ka "
    "qanoon hai.",
}
DISCLAIMER = {
    "en": "For information only, not tax advice. Confirm with a tax practitioner or FBR.",
    "ur": "یہ صرف معلومات کے لیے ہے، ٹیکس مشورہ نہیں۔ کسی ٹیکس ماہر یا ایف بی آر سے تصدیق کریں۔",
    "roman_ur": "Yeh sirf maloomat ke liye hai, tax mashwara nahi. Kisi tax expert ya FBR se "
    "tasdeeq karein.",
}


class AskService:
    def __init__(
        self,
        pipeline: RAGPipeline,
        generator: AnswerGenerator,
        *,
        answer_top_k: int = 6,
        refusal_threshold: float = 0.05,
        last_tax_year: int | None = None,
    ) -> None:
        self.pipeline, self.generator = pipeline, generator
        self.answer_top_k, self.refusal_threshold = answer_top_k, refusal_threshold
        self.first_tax_year = min(c.tax_year_from for c in pipeline.by_id.values())
        # Latest tax year whose law is enacted (the current one); later years are refused.
        self.last_tax_year = last_tax_year

    def ask(
        self,
        question: str,
        tax_year: int | None = None,
        on_stage: Callable[[str], None] | None = None,
    ) -> AskData:
        """`on_stage("search")` / `on_stage("answer")` report progress (the streaming API).
        `timings_ms` gets the per-stage breakdown (backend/app/timing.py, D52)."""
        with request_timer() as timer:
            data = self._ask(question, tax_year, on_stage)
        data.timings_ms.update(timer.result())
        return data

    def _ask(
        self,
        question: str,
        tax_year: int | None,
        on_stage: Callable[[str], None] | None,
    ) -> AskData:
        stage = on_stage or (lambda _: None)
        t0 = time.perf_counter()
        stage("search")
        result = self.pipeline.search(question, tax_year=tax_year)
        t_search = time.perf_counter()
        plan = result.plan
        timings = {"search": int((t_search - t0) * 1000)}

        reason = self._pre_check(result)
        if reason:
            return self._refuse(result, reason, timings)

        top = result.candidates[: self.answer_top_k]
        notes = [
            f"The user mentions {ref}, which does not exist in the law I have."
            for ref in result.missing_refs
        ]
        stage("answer")
        with timed("answer_llm"):
            draft = self.generator.draft(
                question,
                [c.chunk for c in top],
                plan.language,
                plan.tax_year,
                plan.tax_year_assumed,
                notes,
            )
        timings["answer"] = int((time.perf_counter() - t_search) * 1000)
        if not draft.answerable:
            return self._refuse(result, "NOT_IN_SOURCES", timings)

        with timed("citation_check"):
            check = check_citations(
                draft.answer,
                len(top),
                draft.citations,
                # Section numbers of the sources, to spot "section N" mentions nobody cited.
                [(c.chunk.section or "") if c.chunk.law_code != "ITR" else "" for c in top],
            )
        if not check.ok:
            return self._refuse(result, "NO_VALID_CITATIONS", timings)

        warnings = []
        if check.invalid:
            warnings.append(
                f"Removed citations to sources that were not retrieved: {check.invalid}"
            )
        if check.uncited_sentences:
            warnings.append(f"{check.uncited_sentences} sentence(s) without a citation")
        if check.unsupported_sections:
            warnings.append(
                "Mentions sections not among the cited sources: "
                + ", ".join(check.unsupported_sections)
            )
        timings["total"] = int((time.perf_counter() - t0) * 1000)
        return AskData(
            answer=check.text,
            refused=False,
            language=plan.language,
            tax_year=plan.tax_year,
            tax_year_assumed=plan.tax_year_assumed,
            confidence=draft.confidence,
            citations=[self._citation(n, top[n - 1].chunk) for n in check.cited],
            sources=self._sources(result),
            search_queries=plan.queries,
            warnings=warnings,
            disclaimer=DISCLAIMER[plan.language],
            timings_ms=timings,
        )

    def _pre_check(self, result: SearchResult) -> RefusalReason | None:
        plan = result.plan
        if plan.scope != "income_tax":
            return "OUT_OF_SCOPE"
        if plan.tax_year < self.first_tax_year or (
            self.last_tax_year is not None and plan.tax_year > self.last_tax_year
        ):
            return "TAX_YEAR_NOT_COVERED"
        named = any(c.via == "lookup" for c in result.candidates)
        if result.missing_refs and not named:
            return "SECTION_NOT_FOUND"
        if not result.candidates:
            return "NO_RELEVANT_SOURCES"
        top = result.top_score
        if top is not None and top < self.refusal_threshold and not named:
            return "NO_RELEVANT_SOURCES"
        return None

    def _refuse(self, result: SearchResult, reason: RefusalReason, timings: dict) -> AskData:
        plan = result.plan
        lang: Language = plan.language
        future = self.last_tax_year is not None and plan.tax_year > self.last_tax_year
        if reason == "TAX_YEAR_NOT_COVERED" and future:
            text = FUTURE_TAX_YEAR_REFUSAL[lang].format(year=plan.tax_year, last=self.last_tax_year)
        elif reason == "TAX_YEAR_NOT_COVERED":
            text = TAX_YEAR_REFUSAL[lang].format(first=self.first_tax_year, year=plan.tax_year)
        else:
            text = REFUSAL[lang]
        return AskData(
            answer=text,
            refused=True,
            refusal_reason=reason,
            language=lang,
            tax_year=plan.tax_year,
            tax_year_assumed=plan.tax_year_assumed,
            sources=self._sources(result),
            search_queries=plan.queries,
            disclaimer=DISCLAIMER[lang],
            timings_ms=timings,
        )

    @staticmethod
    def _citation(n: int, chunk) -> Citation:
        return Citation(
            n=n,
            chunk_id=chunk.chunk_id,
            section_id=chunk.section_id,
            law=chunk.law,
            label=source_label(chunk),
            text=chunk.text,
            page=chunk.page,
            url=f"{chunk.source_url}#page={chunk.page}",
            version_date=chunk.version_date.isoformat(),
        )

    def _sources(self, result: SearchResult) -> list[Source]:
        return [
            Source(
                rank=c.rank,
                chunk_id=c.chunk_id,
                section_id=c.section_id,
                label=source_label(c.chunk),
                via=c.via,
                rerank_score=round(c.rerank_score, 4) if c.rerank_score is not None else None,
            )
            for c in result.candidates[:10]
        ]
