"""Schema for eval/testset.jsonl — one question per line."""

from typing import Literal

from pydantic import BaseModel, Field

Language = Literal["en", "ur", "roman_ur"]
Group = Literal["english", "urdu", "roman_urdu", "out_of_scope"]
Difficulty = Literal["easy", "medium", "hard"]
QuestionType = Literal["lookup", "rate", "numeric", "multi_section", "conditions", "refusal"]


class TestItem(BaseModel):
    id: str = Field(description="e.g. 'en-001'")
    question: str
    language: Language
    group: Group
    gold_section_ids: list[str] = Field(
        description="Citable units that answer the question (Chunk.section_id); empty = refuse"
    )
    acceptable_section_ids: list[str] = Field(
        default_factory=list,
        description="Other sources that also answer it (e.g. the WHT rate card row for a rate)",
    )
    reference_answer: str = Field(description="Short answer written only from the gold text")
    difficulty: Difficulty
    type: QuestionType
    split: Literal["dev", "test"]
    source_id: str | None = Field(
        default=None, description="For translations: id of the question this was translated from"
    )
    tax_year: int = 2027
    verified: Literal[False, "machine", "reviewed", "human"] = Field(
        default=False,
        description='"machine": passed eval/verify_testset.py (an independent LLM judge, Qwen, '
        'on the gold text and a code check of every number; D45); "reviewed": also judged correct, '
        "or corrected, in the AI legal review of eval/expert_sample.json and re-verified against "
        'the law text (D50); "human": checked by a tax professional',
    )
    second_opinion: Literal["agree", "disagree"] | None = Field(
        default=None,
        description="Second LLM judge (Gemini Flash) on the same check; not blocking (D45). "
        "None = not checked yet",
    )
    language_ok: bool | None = Field(
        default=None,
        description="Urdu / Roman Urdu wording checked by a native speaker (None = not checked)",
    )
    source: Literal["written", "fbr"] = Field(
        default="written",
        description='"fbr": adapted from an FBR-published Q&A (URL in source_url)',
    )
    source_url: str | None = None
    notes: str | None = None
