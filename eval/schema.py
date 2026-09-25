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
    verified: bool = Field(
        default=False, description="Set to true only after a human checked it against the PDF"
    )
    notes: str | None = None
