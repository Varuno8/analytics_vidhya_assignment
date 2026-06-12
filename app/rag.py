import logging

import chromadb
from groq import AsyncGroq

from app import config

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
You are a Python programming Q&A assistant for data science learners. You answer \
questions using the provided Stack Overflow excerpts as your primary source of truth.

Rules:
- Ground your answer in the provided context. When you use information from an \
excerpt, cite it inline as [1], [2], etc. matching the excerpt numbers.
- Include short, runnable code examples where they help.
- If the context does not contain enough information, say so explicitly and then \
give your best general answer, clearly marked as not sourced from the context.
- If the question is not about Python programming, politely say you only answer \
Python programming questions and do not attempt to answer it.
- Be concise and accurate. Prefer modern Python 3 idioms; if an excerpt shows \
Python 2 syntax, modernise it and mention that you did.
"""

USER_PROMPT_TEMPLATE = """\
Stack Overflow excerpts:

{context}

Learner's question: {question}
"""


class Retriever:
    def __init__(self, chroma_dir: str = config.CHROMA_DIR,
                 collection_name: str = config.COLLECTION_NAME):
        client = chromadb.PersistentClient(path=chroma_dir)
        self.collection = client.get_collection(collection_name)

    def count(self) -> int:
        return self.collection.count()

    def query(self, question: str, k: int = config.TOP_K) -> list[dict]:
        res = self.collection.query(
            query_texts=[question],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        hits = []
        for doc, meta, dist in zip(res["documents"][0], res["metadatas"][0], res["distances"][0]):
            hits.append({
                "text": doc,
                "title": meta["title"],
                "url": meta["url"],
                "answer_score": meta["answer_score"],
                "tags": meta.get("tags", ""),
                "relevance": round(max(0.0, 1.0 - dist), 4),
                "distance": dist,
            })
        return hits


def build_context(hits: list[dict]) -> str:
    blocks = []
    for i, h in enumerate(hits, start=1):
        blocks.append(f"[{i}] {h['title']} (answer score: {h['answer_score']})\n{h['text']}")
    return "\n\n---\n\n".join(blocks)


class RAGPipeline:
    def __init__(self, retriever: Retriever):
        self.retriever = retriever
        self.llm = AsyncGroq(api_key=config.GROQ_API_KEY)

    async def ask(self, question: str, top_k: int = config.TOP_K) -> dict:
        hits = self.retriever.query(question, k=top_k)
        relevant = [h for h in hits if h["relevance"] >= config.RELEVANCE_THRESHOLD]
        grounded = len(relevant) > 0
        context_hits = relevant if grounded else hits

        completion = await self.llm.chat.completions.create(
            model=config.GROQ_MODEL,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": USER_PROMPT_TEMPLATE.format(
                    context=build_context(context_hits), question=question)},
            ],
            temperature=0.2,
            max_tokens=1024,
            timeout=config.LLM_TIMEOUT_SECONDS,
        )
        answer = completion.choices[0].message.content

        return {
            "answer": answer,
            "sources": [
                {
                    "title": h["title"],
                    "url": h["url"],
                    "relevance": h["relevance"],
                    "answer_score": h["answer_score"],
                }
                for h in context_hits
            ],
            "grounded": grounded,
            "model": config.GROQ_MODEL,
        }
