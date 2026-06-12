"""Build the Chroma vector index from the raw Stack Overflow parquet shards.

Selection strategy: keep the single best-scored answer per question, then take
the top-N pairs by answer score. High-vote answers are community-verified,
which is what makes the generated answers trustworthy.

Embedding strategy: embeddings are computed from "title + question excerpt"
(what a learner's query actually resembles), while the stored document holds
the full cleaned Q&A text handed to the LLM. all-MiniLM-L6-v2 truncates at
256 tokens, so embedding only the question side loses nothing and matches
query-to-question semantics.
"""
import argparse
import re
import time
from pathlib import Path

import chromadb
import duckdb
from bs4 import BeautifulSoup
from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_GLOB = str(BASE_DIR / "data" / "raw" / "*.parquet")
CHROMA_DIR = str(BASE_DIR / "data" / "chroma")
COLLECTION_NAME = "python_qa"

QUESTION_CHARS = 1200
ANSWER_CHARS = 2500
EMBED_QUESTION_CHARS = 700


def clean_html(html: str) -> str:
    text = BeautifulSoup(html or "", "lxml").get_text("\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def load_pairs(limit: int) -> list[dict]:
    con = duckdb.connect()
    rows = con.execute(
        f"""
        WITH ranked AS (
            SELECT title, question_id, question_body, question_score,
                   answer_id, answer_body, answer_score, tags,
                   ROW_NUMBER() OVER (
                       PARTITION BY question_id ORDER BY answer_score DESC
                   ) AS rn
            FROM read_parquet('{RAW_GLOB}')
        )
        SELECT title, question_id, question_body, question_score,
               answer_id, answer_body, answer_score, tags
        FROM ranked
        WHERE rn = 1 AND answer_score >= 1 AND length(answer_body) > 50
        ORDER BY answer_score DESC
        LIMIT {limit}
        """
    ).fetchall()
    cols = ["title", "question_id", "question_body", "question_score",
            "answer_id", "answer_body", "answer_score", "tags"]
    return [dict(zip(cols, r)) for r in rows]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=30000,
                        help="Number of Q&A pairs to index")
    parser.add_argument("--batch-size", type=int, default=512)
    args = parser.parse_args()

    print(f"Selecting top {args.limit} Q&A pairs from {RAW_GLOB} ...")
    pairs = load_pairs(args.limit)
    print(f"Loaded {len(pairs)} pairs "
          f"(answer scores {pairs[-1]['answer_score']}..{pairs[0]['answer_score']})")

    ef = ONNXMiniLM_L6_V2()
    client = chromadb.PersistentClient(path=CHROMA_DIR)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass
    collection = client.create_collection(
        COLLECTION_NAME, embedding_function=ef, metadata={"hnsw:space": "cosine"}
    )

    start = time.time()
    for batch_start in range(0, len(pairs), args.batch_size):
        batch = pairs[batch_start:batch_start + args.batch_size]
        ids, docs, embed_inputs, metas = [], [], [], []
        for p in batch:
            question = clean_html(p["question_body"])[:QUESTION_CHARS]
            answer = clean_html(p["answer_body"])[:ANSWER_CHARS]
            ids.append(f"{p['question_id']}-{p['answer_id']}")
            docs.append(f"Q: {p['title']}\n{question}\n\nA: {answer}")
            embed_inputs.append(f"{p['title']}\n{question[:EMBED_QUESTION_CHARS]}")
            metas.append({
                "title": p["title"],
                "url": f"https://stackoverflow.com/questions/{p['question_id']}",
                "question_score": int(p["question_score"]),
                "answer_score": int(p["answer_score"]),
                "tags": ",".join(t for t in (p["tags"] or []) if t),
            })
        collection.add(
            ids=ids, documents=docs, metadatas=metas, embeddings=ef(embed_inputs)
        )
        done = batch_start + len(batch)
        rate = done / (time.time() - start)
        print(f"  indexed {done}/{len(pairs)} ({rate:.0f} docs/s)", flush=True)

    print(f"Done. Collection '{COLLECTION_NAME}' has {collection.count()} docs "
          f"at {CHROMA_DIR}")


if __name__ == "__main__":
    main()
