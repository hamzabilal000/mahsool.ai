"""The code half of eval/verify_testset.py: numbers in reference answers vs the law text."""

from collections import defaultdict

from backend.app.llm import LLMError
from backend.app.rag.corpus import load_chunks
from eval.validate_testset import load_testset
from eval.verify_testset import agreement, gold_excerpt, missing_numbers, numbers_in, verify


def test_numbers_in_digits_words_and_brackets():
    text = (
        "Rs. 10 million; ten per cent; 0.8%; [fifty]million rupees; one hundred and "
        "[eighty-three] days; one [and a half]million; [hundred] million; Rs.300,000"
    )
    assert {10, 10_000_000, 0.8, 50_000_000, 183, 1_500_000, 100_000_000, 300_000} <= numbers_in(
        text
    )


def test_legal_references_are_not_quantities():
    ref = "under section 22 or 24, clause (36) of section 2 and the Sixth Schedule, for 3 years"
    assert numbers_in(ref, legal_refs=False) == {3}


def test_missing_numbers_accepts_words_question_inputs_and_worked_arithmetic():
    law = "a surcharge at the rate of ten percent where taxable income exceeds rupees ten million"
    assert (
        missing_numbers("10% where income exceeds Rs. 10 million (tax year 2027)", law, 2027) == []
    )
    assert missing_numbers("the rate is 12%", law, 2027) == [12]
    slab = "where income exceeds Rs.300,000 the rate is 5%"
    ref = (
        "5% of the amount above Rs. 300,000: 500,000 − 300,000 = 200,000; 5% x 200,000 = Rs. 10,000"
    )
    assert missing_numbers(ref, slab, 2027, question="rent of Rs. 500,000") == []
    # the calculation can follow a sentence that ends with an amount
    ref = (
        "5% of the amount exceeding Rs. 300,000. "
        "500,000 − 300,000 = 200,000; 5% x 200,000 = Rs. 10,000."
    )
    assert missing_numbers(ref, slab, 2027, question="rent of Rs. 500,000") == []
    # a wrong result is not accepted
    assert missing_numbers("5% x 200,000 = Rs. 12,000", slab, 2027) == [12_000, 200_000]


def test_long_section_excerpt_keeps_the_chunk_with_the_definition():
    # Section 2 has dozens of chunks sharing "company"; word pairs pick clause (45).
    by_section = defaultdict(list)
    for c in load_chunks():
        by_section[c.section_id].append(c)
    item = next(i for i in load_testset() if i.id == "fbr-021")
    assert '"private company" means a company that is not a public company' in gold_excerpt(
        item, by_section
    ).replace("“", '"').replace("”", '"')


class FakeJudge:
    def __init__(self, name, verdict=None, error=None):
        self.name, self.verdict, self.error, self.calls = name, verdict, error, 0

    def __call__(self, messages):
        self.calls += 1
        if self.error:
            raise LLMError(self.error)
        return {"section_answers_question": "yes", "reference_matches_section": self.verdict}

    def cached(self, messages):
        raise KeyError


def test_second_opinion_never_blocks_and_stops_after_its_daily_limit():
    items = [i for i in load_testset() if i.id in ("en-001", "en-003", "ur-001")]
    ok = FakeJudge("qwen", "yes")
    results = verify(items, ok, FakeJudge("gemini", "no"))
    assert results["en-001"]["ok"] and results["en-001"]["second_opinion"] == "disagree"
    assert results["ur-001"]["second_opinion"] == "disagree"  # inherited from en-003
    assert agreement(results) == (0, 2)

    quota = FakeJudge("gemini", error="daily limit reached")
    results = verify(items, ok, quota)
    assert quota.calls == 1  # not asked again after the daily limit
    assert all(r["ok"] and r["second_opinion"] is None for r in results.values())
