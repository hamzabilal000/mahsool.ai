"""Milestone 3: lookup, query understanding, glossary, reranking, citation check, /ask.

Everything runs without models or network: fake embedder, fake reranker and a scripted LLM.
"""

import re
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from backend.app.llm import LLMError
from backend.app.rag.citations import check_citations
from backend.app.rag.corpus import load_chunks
from backend.app.rag.generator import AnswerGenerator, answer_messages
from backend.app.rag.lookup import SectionLookup
from backend.app.rag.pipeline import PipelineConfig, RAGPipeline
from backend.app.rag.query_rewrite import (
    Glossary,
    QueryRewriter,
    detect_language,
    extract_tax_year,
    rewrite_messages,
)
from backend.app.rag.retriever import Retriever
from backend.app.rag.store import VectorStore, make_client
from backend.app.service import AskService
from tests.backend.test_retrieval import FakeEmbedder, chunk

GLOSSARY = Path("data/glossary_ur.csv")


# --- direct lookup -------------------------------------------------------------------------


@pytest.fixture(scope="module")
def lookup() -> SectionLookup:
    return SectionLookup(load_chunks())


@pytest.mark.parametrize(
    ("question", "expected"),
    [
        ("What does section 149 say?", ["ITO2001-s149"]),
        ("sec. 236k ka rate kya hai", ["ITO2001-s236K"]),
        ("dafa 4AB ke tehat surcharge", ["ITO2001-s4AB"]),
        ("u/s 155 rent", ["ITO2001-s155"]),
        ("دفعہ ۱۴۹ کیا کہتی ہے؟", ["ITO2001-s149"]),
        ("sections 149 and 150", ["ITO2001-s149"]),
        ("rule 5 of the Income Tax Rules", ["ITR2002-r5"]),
        ("qaida 13P", ["ITR2002-r13P"]),
        ("Income Tax Rules 2002 mein kya hai", []),  # a year is not a rule number
        ("salary 149 hai", []),  # a bare number is not a reference
    ],
)
def test_lookup_finds_named_sections(lookup, question, expected):
    assert [r.section_id for r in lookup.find(question)] == expected


def test_lookup_reports_sections_that_do_not_exist(lookup):
    refs, missing = lookup.resolve("What does section 999Z say about crypto mining?")
    assert refs == [] and missing == ["section 999Z"]


# --- language, tax year, glossary ----------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "lang"),
    [
        ("How is salary taxed?", "en"),
        ("non filer hun, bank se cash nikalwaun to kitna tax katega?", "roman_ur"),
        ("میری تنخواہ پر کتنا ٹیکس کٹے گا؟", "ur"),
        ("Is the ATL list updated every year?", "en"),
        ("section 149 ka rate kya hai", "roman_ur"),
    ],
)
def test_detect_language(text, lang):
    assert detect_language(text) == lang


@pytest.mark.parametrize(
    ("text", "year"),
    [
        ("tax year 2025 me salary tax", 2025),
        ("What was the rate in TY2024?", 2024),
        ("rate for 2024-25", 2025),
        ("ٹیکس سال ۲۰۲۶ میں", 2026),
        ("Rs. 2000-50 range", None),
        ("How much tax on salary?", None),
    ],
)
def test_extract_tax_year(text, year):
    assert extract_tax_year(text) == year


def test_glossary_matches_roman_and_urdu_spellings():
    g = Glossary.load(GLOSSARY)
    roman = [e.english for _, e in g.match("non filer hun, property khareedni hai")]
    assert any("non-ATL" in e for e in roman)
    assert any("purchase" in e for e in roman)
    urdu = [e.english for _, e in g.match("کرایہ کی آمدنی پر ٹیکس")]
    assert any("rent" in e for e in urdu)
    # Word boundaries: "kat" must not match inside "katrina".
    assert not any(t == "kat" for t, _ in g.match("katrina"))
    # Urdu terms must start a word: "دن" (days) is not inside "آمدن" (income).
    assert not any(t == "دن" for t, _ in g.match("غیر ملکی آمدن"))
    assert any(t == "دن" for t, _ in g.match("183 دن سے زیادہ"))


def test_glossary_section_ids_exist():
    ids = {c.section_id for c in load_chunks()}
    g = Glossary.load(GLOSSARY)
    assert len(g.entries) >= 150
    assert all(s in ids for e in g.entries for s in e.section_ids)


def test_rewrite_prompt_includes_glossary_hints_only_when_given():
    g = Glossary.load(GLOSSARY)
    with_hints = rewrite_messages("filer nahi hun", g.match("filer nahi hun"))[1]["content"]
    assert "Glossary" in with_hints and "Active Taxpayers" in with_hints
    assert "Glossary" not in rewrite_messages("filer nahi hun", [])[1]["content"]


class ScriptedLLM:
    """Returns canned JSON per call, and records the prompts."""

    def __init__(self, *outputs: dict) -> None:
        self.outputs = list(outputs)
        self.calls: list[list[dict]] = []

    def chat_json(self, model, messages, **kw):
        self.calls.append(messages)
        if not self.outputs:
            raise LLMError("no scripted output left")
        return self.outputs.pop(0)


def test_rewriter_keeps_rule_based_year_and_ignores_invented_year():
    llm = ScriptedLLM({"queries": ["salary tax rates"], "tax_year": 2024, "scope": "income_tax"})
    plan = QueryRewriter(llm, "m", current_tax_year=2027).plan("salary pe kitna tax hai?")
    assert plan.queries == ["salary tax rates"]
    assert plan.tax_year == 2027 and plan.tax_year_assumed  # 2024 is not in the question


def test_rewriter_without_llm_only_detects():
    plan = QueryRewriter(None, "m").plan("tax year 2025 salary", rewrite=True)
    assert plan.queries == [] and plan.tax_year == 2025 and not plan.tax_year_assumed


# --- citation check ------------------------------------------------------------------------


def test_citation_check_removes_invented_sources():
    c = check_citations("Tax is deducted monthly [1]. The rate is 5% [7].", n_sources=3)
    assert c.cited == [1] and c.invalid == [7]
    assert "[7]" not in c.text and c.ok


def test_citation_check_fails_when_nothing_valid_is_cited():
    assert not check_citations("The rate is 5% [9].", n_sources=3).ok
    assert not check_citations("The rate is 5%.", n_sources=3).ok


def test_citation_check_warns_on_uncited_sentences_and_sections():
    c = check_citations(
        "Under section 149 the employer deducts tax [1]. Section 236K also applies here.",
        n_sources=2,
        source_sections=["149", "155"],
    )
    assert c.uncited_sentences == 1
    assert c.unsupported_sections == ["236K"]


# --- pipeline and service ------------------------------------------------------------------


class KeywordReranker:
    """Scores a passage by the share of query words it contains."""

    def score(self, query, passages):
        words = {w for w in re.findall(r"[a-z]+", query.lower()) if len(w) > 4}
        return [sum(w in p.lower() for w in words) / max(len(words), 1) for p in passages]


CORPUS = [
    chunk("ITO2001-s149", "Every employer paying salary shall deduct tax at the average rate"),
    chunk(
        "ITO2001-s155", "Tax shall be deducted from the gross amount of rent of immovable property"
    ),
    chunk("ITO2001-s236K", "Advance tax on purchase of immovable property at fair market value"),
    chunk("ITO2001-s181A", "Active taxpayers list published by the Board every year"),
]


@pytest.fixture
def make_pipeline():
    def _make(config: PipelineConfig, llm=None) -> RAGPipeline:
        emb = FakeEmbedder()
        store = VectorStore(make_client(None, in_memory=True), "t", emb.dim)
        store.recreate()
        store.upsert(CORPUS, emb.encode([c.text for c in CORPUS]))
        retriever = Retriever(CORPUS, "hybrid", store=store, embedder=emb, tax_year=2027)
        rewriter = QueryRewriter(llm, "m", Glossary.load(GLOSSARY))
        return RAGPipeline(CORPUS, retriever, rewriter, KeywordReranker(), config)

    return _make


def test_pipeline_pins_named_section_first(make_pipeline):
    p = make_pipeline(PipelineConfig(rewrite="none", rerank=True))
    res = p.search("section 155: is tax deducted from salary?")
    assert res.candidates[0].section_id == "ITO2001-s155"
    assert res.candidates[0].via == "lookup"


def test_pipeline_uses_rewrites(make_pipeline):
    llm = ScriptedLLM(
        {"queries": ["advance tax on purchase of immovable property"], "scope": "income_tax"}
    )
    p = make_pipeline(PipelineConfig(rewrite="glossary", rerank=False), llm)
    res = p.search("plot khareedne pe kitna tax?")
    assert res.plan.queries == ["advance tax on purchase of immovable property"]
    assert res.candidates[0].section_id == "ITO2001-s236K"
    # The glossary hint for "khareed..." is not in this question, but "plot" is.
    assert "plot" in llm.calls[0][1]["content"]


def test_pipeline_rerank_with_max_of_question_and_rewrite(make_pipeline):
    def llm():
        return ScriptedLLM(
            {"queries": ["advance tax on purchase of immovable property"], "scope": "income_tax"}
        )

    question = "plot khareedne pe kitna tax?"  # no word the keyword reranker can use
    only_question = make_pipeline(PipelineConfig(rewrite="plain"), llm()).search(question)
    assert only_question.top_score == 0
    config = PipelineConfig(rewrite="plain", rerank_query="max")
    both = make_pipeline(config, llm()).search(question)
    assert both.candidates[0].section_id == "ITO2001-s236K"
    assert both.top_score > 0


def test_pipeline_ablation_switches(make_pipeline):
    p = make_pipeline(PipelineConfig(lookup=False, rewrite="none", rerank=False))
    res = p.search("section 155 salary")
    assert all(c.via == "search" for c in res.candidates)
    assert all(c.rerank_score is None for c in res.candidates)


def answer(text: str, cites: list[int], answerable: bool = True) -> dict:
    return {"answerable": answerable, "answer": text, "citations": cites, "confidence": "high"}


def rewrite(scope: str = "income_tax", queries=("tax deducted from salary by employer",)):
    return {"queries": list(queries), "scope": scope, "tax_year": None}


def service(make_pipeline, *outputs, threshold: float = 0.05) -> AskService:
    llm = ScriptedLLM(*outputs)
    p = make_pipeline(PipelineConfig(rewrite="glossary", rerank=True), llm)
    return AskService(p, AnswerGenerator(llm, "big"), answer_top_k=3, refusal_threshold=threshold)


def test_service_answers_with_valid_citations(make_pipeline):
    s = service(make_pipeline, rewrite(), answer("The employer deducts tax [1]. Also [9].", [1]))
    data = s.ask("salary pe tax kaun deduct karta hai?")
    assert not data.refused and data.language == "roman_ur"
    assert [c.n for c in data.citations] == [1]
    assert data.citations[0].url.endswith("#page=1")
    assert "[9]" not in data.answer
    assert data.tax_year == 2027 and data.tax_year_assumed
    assert data.disclaimer.startswith("Yeh sirf")


@pytest.mark.parametrize(
    ("question", "outputs", "reason"),
    [
        ("PRA restaurant tax?", [rewrite("provincial_tax")], "OUT_OF_SCOPE"),
        ("tax year 2020 salary", [rewrite()], "TAX_YEAR_NOT_COVERED"),
        ("What does section 999Z say?", [rewrite()], "SECTION_NOT_FOUND"),
        ("salary tax?", [rewrite(), answer("", [], answerable=False)], "NOT_IN_SOURCES"),
        ("salary tax?", [rewrite(), answer("Tax is 5% [8].", [8])], "NO_VALID_CITATIONS"),
    ],
)
def test_service_refusals(make_pipeline, question, outputs, reason):
    data = service(make_pipeline, *outputs).ask(question)
    assert data.refused and data.refusal_reason == reason
    assert data.citations == []


def test_service_refuses_future_tax_year(make_pipeline):
    llm = ScriptedLLM(rewrite())
    p = make_pipeline(PipelineConfig(rewrite="glossary", rerank=True), llm)
    s = AskService(p, AnswerGenerator(llm, "big"), last_tax_year=2027)
    data = s.ask("salary tax slabs for tax year 2028?")
    assert data.refusal_reason == "TAX_YEAR_NOT_COVERED"
    assert "2028" in data.answer and "has not been made" in data.answer


def test_service_refuses_on_low_reranker_score_without_calling_answer_model(make_pipeline):
    s = service(make_pipeline, rewrite(queries=[]), threshold=0.99)
    data = s.ask("zzzzz qqqqq xxxxx")
    assert data.refusal_reason == "NO_RELEVANT_SOURCES"  # ScriptedLLM had no answer to give


def test_refusal_is_in_the_users_language(make_pipeline):
    data = service(make_pipeline, rewrite("not_tax")).ask("کرکٹ میچ کب ہے؟")
    assert data.language == "ur" and "مجھے" in data.answer


def test_answer_prompt_numbers_sources_and_sets_language():
    msgs = answer_messages("q?", CORPUS[:2], "ur", 2027, True)
    assert "Urdu in Urdu script" in msgs[0]["content"]
    assert "[1] Test" in msgs[1]["content"] and "[2] Test" in msgs[1]["content"]
    assert "tax year 2027" in msgs[1]["content"]


# --- HTTP API ------------------------------------------------------------------------------


@pytest.fixture
def client(make_pipeline):
    from backend.app.main import create_app

    s = service(make_pipeline, rewrite(), answer("The employer deducts tax [1].", [1]))
    return TestClient(create_app(service=s))


def test_ask_returns_envelope(client):
    r = client.post("/ask", json={"question": "Who deducts tax from salary?"})
    body = r.json()
    assert r.status_code == 200
    assert body["success"] is True and body["code"] == "OK" and body["error"] is None
    assert body["data"]["citations"][0]["section_id"] == "ITO2001-s149"


def test_ask_validation_error_uses_envelope(client):
    r = client.post("/ask", json={"question": "x"})
    body = r.json()
    assert r.status_code == 422
    assert body["success"] is False and body["code"] == "VALIDATION_ERROR" and body["data"] is None


def test_ask_llm_failure_is_503(client):
    # The scripted LLM has one rewrite and one answer; the second question runs out.
    client.post("/ask", json={"question": "Who deducts tax from salary?"})
    r = client.post("/ask", json={"question": "Who deducts tax from salary?"})
    assert r.status_code == 503 and r.json()["code"] == "LLM_UNAVAILABLE"


def test_ask_rate_limit(make_pipeline):
    from backend.app.api.ask import RateLimiter
    from backend.app.main import create_app

    app = create_app(service=service(make_pipeline))
    app.state.limiter = RateLimiter(limit=0)
    r = TestClient(app).post("/ask", json={"question": "Who deducts tax?"})
    assert r.status_code == 429 and r.json()["code"] == "RATE_LIMITED"


def test_health(client):
    assert client.get("/health").json()["success"] is True


def test_groq_client_fails_fast_on_daily_limit():
    from backend.app.llm import GroqClient

    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(429, text='{"error": {"message": "... tokens per day (TPD) ..."}}')

    client = GroqClient("key")
    client.http = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(LLMError, match="daily limit"):
        client.chat_json("m", [{"role": "user", "content": "hi"}])
    assert len(calls) == 1  # no retries


def test_answer_prompt_requires_conditions_atl_rates_and_who_it_applies_to():
    system = answer_messages("q", [], "en", 2027, False)[0]["content"]
    assert "Active Taxpayers' List" in system and "give both" in system
    assert "prescribed person" in system and "conditional" in system
    assert "Do not add conditions that are not in the sources" in system
