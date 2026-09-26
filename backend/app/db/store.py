"""Two tables, created on startup if missing (DECISIONS D47):

- `asks`: one row per answered or refused question (question, language, tax year, answer,
  citations, refusal reason, timings). No IP address or user id is stored.
- `feedback`: thumbs up / down (and an optional comment) on an ask; one vote per ask, a new vote
  replaces the old one.

SQLAlchemy Core, so the same code runs on Postgres (Neon, via psycopg 3) and on SQLite.
"""

import uuid
from datetime import UTC, datetime
from pathlib import Path

from sqlalchemy import (
    JSON,
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    String,
    Table,
    Text,
    create_engine,
    delete,
    func,
    insert,
    select,
)
from sqlalchemy.engine import Engine

from backend.app.models.schemas import AskData

metadata = MetaData()

asks = Table(
    "asks",
    metadata,
    Column("id", String(36), primary_key=True),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("question", Text, nullable=False),
    Column("language", String(10), nullable=False),
    Column("tax_year", Integer, nullable=False),
    Column("refused", Boolean, nullable=False),
    Column("refusal_reason", String(40)),
    Column("answer", Text, nullable=False),
    Column("citations", JSON, nullable=False),  # section ids, in answer order
    Column("confidence", String(10)),
    Column("timings_ms", JSON, nullable=False),
)

feedback = Table(
    "feedback",
    metadata,
    Column("id", Integer, primary_key=True, autoincrement=True),
    Column("ask_id", String(36), ForeignKey("asks.id", ondelete="CASCADE"), nullable=False),
    Column("created_at", DateTime(timezone=True), nullable=False),
    Column("rating", String(4), nullable=False),  # "up" | "down"
    Column("comment", Text),
)


def database_url(url: str | None, sqlite_path: Path) -> str:
    """SQLAlchemy URL: Postgres from DATABASE_URL (psycopg 3 driver), else a SQLite file."""
    if not url:
        sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        return f"sqlite:///{sqlite_path}"
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix) :]
    return url


class FeedbackStore:
    def __init__(self, url: str) -> None:
        self.engine: Engine = create_engine(url, pool_pre_ping=True)
        metadata.create_all(self.engine)

    @property
    def kind(self) -> str:
        return self.engine.dialect.name  # "postgresql" or "sqlite"

    def log_ask(self, question: str, data: AskData) -> str:
        ask_id = str(uuid.uuid4())
        with self.engine.begin() as conn:
            conn.execute(
                insert(asks).values(
                    id=ask_id,
                    created_at=datetime.now(UTC),
                    question=question,
                    language=data.language,
                    tax_year=data.tax_year,
                    refused=data.refused,
                    refusal_reason=data.refusal_reason,
                    answer=data.answer,
                    citations=[c.section_id for c in data.citations],
                    confidence=data.confidence,
                    timings_ms=data.timings_ms,
                )
            )
        return ask_id

    def add_feedback(self, ask_id: str, rating: str, comment: str | None = None) -> bool:
        """False if the ask does not exist."""
        with self.engine.begin() as conn:
            if conn.execute(select(asks.c.id).where(asks.c.id == ask_id)).first() is None:
                return False
            conn.execute(delete(feedback).where(feedback.c.ask_id == ask_id))
            conn.execute(
                insert(feedback).values(
                    ask_id=ask_id, created_at=datetime.now(UTC), rating=rating, comment=comment
                )
            )
        return True

    def feedback_counts(self) -> dict[str, int]:
        with self.engine.connect() as conn:
            rows = conn.execute(
                select(feedback.c.rating, func.count()).group_by(feedback.c.rating)
            ).all()
        return {rating: n for rating, n in rows}
