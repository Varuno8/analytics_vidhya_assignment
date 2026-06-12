from pydantic import BaseModel, Field

from app import config


class AskRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=config.MAX_QUESTION_LEN)
    top_k: int = Field(default=config.TOP_K, ge=1, le=10)


class Source(BaseModel):
    title: str
    url: str
    relevance: float
    answer_score: int


class AskResponse(BaseModel):
    answer: str
    sources: list[Source]
    grounded: bool
    model: str
    latency_ms: int
    cached: bool = False


class HealthResponse(BaseModel):
    status: str
    index_size: int
    model: str
