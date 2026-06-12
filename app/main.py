import logging
import time
from collections import OrderedDict
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.responses import RedirectResponse
from groq import GroqError

from app import config
from app.rag import RAGPipeline, Retriever
from app.schemas import AskRequest, AskResponse, HealthResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_answer_cache: OrderedDict[str, dict] = OrderedDict()


@asynccontextmanager
async def lifespan(app: FastAPI):
    retriever = Retriever()
    app.state.pipeline = RAGPipeline(retriever)
    logger.info("Index loaded: %d documents", retriever.count())
    yield


app = FastAPI(
    title="Python Programming Q&A Assistant",
    description=(
        "RAG-powered Q&A over the Stack Overflow Python dataset "
        "(Kaggle: stackoverflow/pythonquestions), answered by Llama on Groq."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/", include_in_schema=False)
async def root():
    return RedirectResponse(url="/docs")


@app.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(
        status="ok",
        index_size=app.state.pipeline.retriever.count(),
        model=config.GROQ_MODEL,
    )


@app.post("/ask", response_model=AskResponse)
async def ask(req: AskRequest):
    cache_key = f"{req.question.strip().lower()}|{req.top_k}"
    if cache_key in _answer_cache:
        cached = _answer_cache[cache_key]
        return AskResponse(**{**cached, "cached": True, "latency_ms": 0})

    start = time.perf_counter()
    try:
        result = await app.state.pipeline.ask(req.question, top_k=req.top_k)
    except GroqError as e:
        logger.exception("LLM call failed")
        raise HTTPException(status_code=502, detail=f"LLM provider error: {e}") from e

    result["latency_ms"] = int((time.perf_counter() - start) * 1000)

    _answer_cache[cache_key] = result
    if len(_answer_cache) > config.ANSWER_CACHE_SIZE:
        _answer_cache.popitem(last=False)

    return AskResponse(**result)
