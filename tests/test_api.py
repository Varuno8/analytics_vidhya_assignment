"""API tests. LLM and retriever are mocked so tests run without an index or API key."""
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


FAKE_RESULT = {
    "answer": "Use `sorted(my_list, reverse=True)` [1].",
    "sources": [{
        "title": "How to sort a list in descending order",
        "url": "https://stackoverflow.com/questions/123",
        "relevance": 0.82,
        "answer_score": 250,
    }],
    "grounded": True,
    "model": "llama-3.1-8b-instant",
}


@pytest.fixture
def client():
    pipeline = MagicMock()
    pipeline.ask = AsyncMock(return_value=dict(FAKE_RESULT))
    pipeline.retriever.count.return_value = 30000
    app.state.pipeline = pipeline
    main_module._answer_cache.clear()
    # No context manager: skips lifespan, which needs a real index on disk.
    yield TestClient(app)


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["index_size"] == 30000
    assert "model" in body


def test_ask_returns_grounded_answer(client):
    r = client.post("/ask", json={"question": "How do I sort a list in descending order?"})
    assert r.status_code == 200
    body = r.json()
    assert "sorted" in body["answer"]
    assert body["grounded"] is True
    assert len(body["sources"]) == 1
    assert body["sources"][0]["url"].startswith("https://stackoverflow.com/")
    assert body["cached"] is False
    assert body["latency_ms"] >= 0


def test_ask_caches_repeated_question(client):
    q = {"question": "How do I sort a list in descending order?"}
    first = client.post("/ask", json=q)
    second = client.post("/ask", json=q)
    assert first.json()["cached"] is False
    assert second.json()["cached"] is True
    app.state.pipeline.ask.assert_awaited_once()


def test_ask_rejects_empty_question(client):
    r = client.post("/ask", json={"question": ""})
    assert r.status_code == 422


def test_ask_rejects_too_long_question(client):
    r = client.post("/ask", json={"question": "x" * 5000})
    assert r.status_code == 422


def test_ask_rejects_bad_top_k(client):
    r = client.post("/ask", json={"question": "What is a dict?", "top_k": 50})
    assert r.status_code == 422


def test_ask_missing_body(client):
    r = client.post("/ask", json={})
    assert r.status_code == 422


def test_llm_failure_returns_502(client):
    from groq import GroqError
    app.state.pipeline.ask = AsyncMock(side_effect=GroqError("rate limit"))
    r = client.post("/ask", json={"question": "What is a generator in Python?"})
    assert r.status_code == 502
    assert "LLM provider error" in r.json()["detail"]
