"""Milestone 4 API: question log + feedback store, streamed answers, eval page data."""

import json

import pytest
from fastapi.testclient import TestClient

from backend.app.db import FeedbackStore, database_url
from backend.app.main import create_app
from tests.backend.test_pipeline import answer, make_pipeline, rewrite, service  # noqa: F401


@pytest.fixture
def store(tmp_path):
    return FeedbackStore(database_url(None, tmp_path / "t.db"))


@pytest.fixture
def api(make_pipeline, store):  # noqa: F811
    s = service(make_pipeline, rewrite(), answer("The employer deducts tax [1].", [1]))
    return TestClient(create_app(service=s, store=store))


def test_database_url_uses_psycopg_for_postgres_and_sqlite_otherwise(tmp_path):
    neon = "postgresql://u:p@ep-x.aws.neon.tech/mahsool?sslmode=require"
    assert database_url(neon, tmp_path / "x.db").startswith("postgresql+psycopg://u:p@ep-x")
    assert database_url("postgres://u@h/db", tmp_path / "x.db") == "postgresql+psycopg://u@h/db"
    assert database_url(None, tmp_path / "x.db") == f"sqlite:///{tmp_path / 'x.db'}"


def test_ask_is_logged_and_feedback_is_stored_once_per_answer(api, store):
    data = api.post("/ask", json={"question": "Who deducts tax from salary?"}).json()["data"]
    assert data["id"]
    r = api.post("/feedback", json={"ask_id": data["id"], "rating": "down", "comment": "slow"})
    assert r.status_code == 200 and r.json()["success"] is True
    api.post("/feedback", json={"ask_id": data["id"], "rating": "up"})  # replaces the vote
    assert store.feedback_counts() == {"up": 1}


def test_feedback_rejects_unknown_answers_and_bad_ratings(api):
    r = api.post("/feedback", json={"ask_id": "nope", "rating": "up"})
    assert r.status_code == 404 and r.json()["code"] == "NOT_FOUND"
    r = api.post("/feedback", json={"ask_id": "x", "rating": "meh"})
    assert r.status_code == 422 and r.json()["code"] == "VALIDATION_ERROR"


def parse_sse(text: str) -> list[tuple[str, dict]]:
    events = []
    for block in text.strip().split("\n\n"):
        lines = dict(line.split(": ", 1) for line in block.splitlines())
        events.append((lines["event"], json.loads(lines["data"])))
    return events


def test_stream_sends_stages_then_the_checked_answer_then_the_envelope(api):
    r = api.post("/ask/stream", json={"question": "Who deducts tax from salary?"})
    assert r.headers["content-type"].startswith("text/event-stream")
    events = parse_sse(r.text)
    kinds = [e for e, _ in events]
    assert kinds[:2] == ["stage", "stage"] and [d["stage"] for _, d in events[:2]] == [
        "search",
        "answer",
    ]
    assert kinds[-1] == "done"
    done = events[-1][1]
    assert done["success"] is True and done["data"]["id"]
    streamed = "".join(d["text"] for e, d in events if e == "delta")
    assert streamed == done["data"]["answer"]


def test_stream_rate_limit_is_an_error_event(api):
    api.app.state.limiter.limit = 0
    events = parse_sse(api.post("/ask/stream", json={"question": "Who deducts tax?"}).text)
    assert events == [("error", events[0][1])] and events[0][1]["code"] == "RATE_LIMITED"


def test_eval_summary_and_chart_are_served(api):
    body = api.get("/eval/summary").json()
    assert body["success"] is True
    assert body["data"]["testset"]["questions"] >= 239
    assert body["data"]["retrieval_ablation"][-1]["setup"] == "Full, max score"
    r = api.get("/eval/ablation.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"


def test_cors_allows_the_vite_dev_server_with_credentials(api):
    r = api.options(
        "/ask",
        headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"},
    )
    assert r.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert r.headers["access-control-allow-credentials"] == "true"
