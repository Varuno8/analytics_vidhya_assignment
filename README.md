# Python Programming Q&A Assistant

A retrieval-augmented generation (RAG) system that answers Python programming
questions for data science learners, grounded in the
[Stack Overflow Python Questions dataset](https://www.kaggle.com/datasets/stackoverflow/pythonquestions).

**Live demo:** [huggingface.co/spaces/varun2808/python-qa-assistant](https://huggingface.co/spaces/varun2808/python-qa-assistant) | API: [varun2808-python-qa-assistant.hf.space](https://varun2808-python-qa-assistant.hf.space)

## How it works

```text
                        ┌──────────────────────────────────────────┐
 user question ──POST──▶│ FastAPI  /ask                            │
                        │   1. embed question (MiniLM-L6, ONNX)    │
                        │   2. ChromaDB top-k similar SO questions │
                        │   3. relevance gate (cosine threshold)   │
                        │   4. Groq Llama 3.1 8B + grounded prompt │
                        │   5. answer + cited SO sources           │
                        └──────────────────────────────────────────┘
                                       ▲
        offline: parquet shards ─▶ best answer per question ─▶ top 30k by
        votes ─▶ HTML→text ─▶ embed title+question ─▶ persistent Chroma index
```

- **Corpus:** 987k Q&A rows reduced to the top **30,000** question/answer pairs
  (best-voted answer per question, ranked by answer score). High-vote answers are
  community-verified, which keeps generation grounded in trusted content.
- **Retrieval:** ChromaDB (cosine HNSW) with `all-MiniLM-L6-v2` ONNX embeddings —
  no PyTorch, light enough for free-tier hosting. Queries match against
  *question* embeddings; the LLM receives the full Q&A text.
- **Generation:** Llama 3.1 8B Instant via Groq, prompted to cite excerpts
  inline (`[1]`, `[2]`), flag unsourced claims, and decline non-Python questions.
- **Guardrail:** if no retrieved document passes the relevance threshold the
  response is marked `"grounded": false`.

## API

| Method | Path      | Description                                  |
|--------|-----------|----------------------------------------------|
| POST   | `/ask`    | Ask a Python question, get a grounded answer |
| GET    | `/health` | Service + index status                       |
| GET    | `/docs`   | Interactive OpenAPI docs                     |

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -d '{"question": "How do I merge two dictionaries in Python?"}'
```

```json
{
  "answer": "Use the | operator (Python 3.9+): merged = d1 | d2 [1] ...",
  "sources": [
    {"title": "How do I merge two dictionaries...", "url": "https://stackoverflow.com/questions/38987",
     "relevance": 0.81, "answer_score": 5876}
  ],
  "grounded": true,
  "model": "llama-3.1-8b-instant",
  "latency_ms": 1240,
  "cached": false
}
```

## Setup

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # add your GROQ_API_KEY

# 1. Download the dataset (~830 MB parquet, no Kaggle account needed)
python scripts/download_data.py

# 2. Build the vector index (~10 min on a laptop CPU)
python scripts/build_index.py --limit 30000

# 3. Run the API
uvicorn app.main:app --reload
```

Open <http://localhost:8000/docs> to try it.

## Testing

```bash
pytest                       # unit + integration tests (LLM mocked)
python run_test_queries.py   # 10 live queries -> TEST_RESULTS.md
```

See [TEST_RESULTS.md](TEST_RESULTS.md) for documented queries, responses, and
observations including edge cases (vague queries, off-topic questions,
validation failures).

## Environment variables

See [.env.example](.env.example). Only `GROQ_API_KEY` is required.

## Deployment

The included [Dockerfile](Dockerfile) serves the app with the prebuilt index baked
in (build the index first, then `docker build`). Works on Hugging Face Spaces
(Docker SDK, port 7860), Render, or Railway — set `GROQ_API_KEY` as a secret.

## Project structure

```text
app/            FastAPI service + RAG pipeline
scripts/        dataset download + index build
tests/          pytest suite (API mocked, retrieval integration)
run_test_queries.py   live test harness -> TEST_RESULTS.md
slides/         design deck
```
