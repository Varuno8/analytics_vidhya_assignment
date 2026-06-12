"""Integration test against the real Chroma index (skipped if not built)."""
from pathlib import Path

import pytest

CHROMA_DIR = Path(__file__).resolve().parent.parent / "data" / "chroma"

pytestmark = pytest.mark.skipif(
    not CHROMA_DIR.exists(), reason="Chroma index not built (run scripts/build_index.py)"
)


@pytest.fixture(scope="module")
def retriever():
    from app.rag import Retriever
    return Retriever()


def test_index_is_populated(retriever):
    assert retriever.count() > 10000


def test_relevant_retrieval_for_common_question(retriever):
    hits = retriever.query("How do I reverse a list in Python?", k=5)
    assert len(hits) == 5
    assert hits[0]["relevance"] > 0.5
    combined = " ".join(h["title"].lower() for h in hits)
    assert "list" in combined or "revers" in combined


def test_hits_carry_stackoverflow_urls(retriever):
    hits = retriever.query("What does the yield keyword do?", k=3)
    for h in hits:
        assert h["url"].startswith("https://stackoverflow.com/questions/")
        assert isinstance(h["answer_score"], int)


def test_off_topic_question_has_low_relevance(retriever):
    hits = retriever.query("What is the best recipe for chocolate cake?", k=3)
    assert hits[0]["relevance"] < 0.5
