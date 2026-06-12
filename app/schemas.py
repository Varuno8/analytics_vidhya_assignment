"""Pydantic request/response models for the API."""
from pydantic import BaseModel, Field

from app import config


class AskRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        max_length=config.MAX_QUESTION_LEN,
        description="A Python programming question in natural language.",
        examples=["How do I merge two dictionaries in Python?"],
    )
    top_k: int = Field(
        default=config.TOP_K,
        ge=1,
        le=10,
        description="Number of Stack Overflow Q&A pairs to retrieve for grounding.",
    )


class Source(BaseModel):
    title: str
    url: str
    relevance: float = Field(description="Similarity score in [0, 1]; higher is more relevant.")
    answer_score: int = Field(description="Stack Overflow vote count of the answer used.")


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    grounded: bool = Field(
        description="False when no sufficiently relevant Stack Overflow context was found."
    )
    model: str
    latency_ms: int
    cached: bool = False


class HealthResponse(BaseModel):
    status: str
    index_size: int
    model: str
