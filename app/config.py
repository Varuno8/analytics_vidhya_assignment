"""Application configuration, loaded from environment variables."""
import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = os.getenv("GROQ_MODEL", "llama-3.1-8b-instant")

CHROMA_DIR = os.getenv("CHROMA_DIR", str(BASE_DIR / "data" / "chroma"))
COLLECTION_NAME = os.getenv("COLLECTION_NAME", "python_qa")

TOP_K = int(os.getenv("TOP_K", "5"))
# Cosine distance above which a retrieved doc is considered irrelevant.
RELEVANCE_THRESHOLD = float(os.getenv("RELEVANCE_THRESHOLD", "0.50"))
MAX_QUESTION_LEN = int(os.getenv("MAX_QUESTION_LEN", "2000"))
ANSWER_CACHE_SIZE = int(os.getenv("ANSWER_CACHE_SIZE", "256"))
LLM_TIMEOUT_SECONDS = float(os.getenv("LLM_TIMEOUT_SECONDS", "30"))
