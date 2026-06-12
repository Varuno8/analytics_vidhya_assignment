"""Run a diverse set of live test queries against the API and write TEST_RESULTS.md.

Usage: start the server (uvicorn app.main:app), then:
    python run_test_queries.py [--base-url http://localhost:8000]
"""
import argparse
import json
import time

import httpx

TEST_QUERIES = [
    # Core language basics
    ("Basic", "How do I reverse a list in Python?"),
    ("Basic", "What is the difference between a list and a tuple?"),
    # Common practical tasks
    ("Practical", "How do I read a file line by line in Python?"),
    ("Practical", "How do I merge two dictionaries?"),
    # Conceptual / intermediate
    ("Conceptual", "What does if __name__ == '__main__' do?"),
    ("Conceptual", "Explain Python decorators with a simple example."),
    ("Conceptual", "What is the difference between deepcopy and shallow copy?"),
    # Data-science flavoured (target audience)
    ("Data science", "How do I select rows in a pandas DataFrame where a column matches a value?"),
    # Edge cases
    ("Edge: vague", "my code is slow how to make fast"),
    ("Edge: off-topic", "What is the capital of France?"),
]


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--out", default="TEST_RESULTS.md")
    args = parser.parse_args()

    client = httpx.Client(base_url=args.base_url, timeout=120)

    health = client.get("/health").json()
    print("health:", health)

    results = []
    for category, question in TEST_QUERIES:
        print(f"\n=== [{category}] {question}")
        t0 = time.time()
        r = client.post("/ask", json={"question": question})
        elapsed = time.time() - t0
        body = r.json() if r.status_code == 200 else {"error": r.text}
        results.append({
            "category": category, "question": question,
            "status": r.status_code, "elapsed_s": round(elapsed, 2), "response": body,
        })
        print(f"    -> {r.status_code} in {elapsed:.1f}s, "
              f"grounded={body.get('grounded')}, sources={len(body.get('sources', []))}")

    # Also document validation behaviour.
    bad = client.post("/ask", json={"question": ""})
    results.append({
        "category": "Edge: validation", "question": "(empty string)",
        "status": bad.status_code, "elapsed_s": 0.0,
        "response": bad.json(),
    })

    with open(args.out, "w") as f:
        f.write("# API Test Results\n\n")
        f.write(f"- Index size: **{health['index_size']}** Stack Overflow Q&A pairs\n")
        f.write(f"- Model: **{health['model']}** (Groq)\n")
        f.write(f"- Endpoint: `POST /ask`\n\n")
        for i, res in enumerate(results, 1):
            f.write(f"## {i}. [{res['category']}] {res['question']}\n\n")
            f.write(f"- **HTTP status:** {res['status']}  \n")
            f.write(f"- **Latency:** {res['elapsed_s']}s\n\n")
            resp = res["response"]
            if "answer" in resp:
                f.write(f"- **Grounded:** {resp['grounded']}\n")
                srcs = ", ".join(
                    f"[{s['title']}]({s['url']}) (▲{s['answer_score']}, rel {s['relevance']:.2f})"
                    for s in resp["sources"][:3]
                )
                f.write(f"- **Top sources:** {srcs}\n\n")
                f.write("**Answer:**\n\n")
                f.write(f"{resp['answer']}\n\n")
            else:
                f.write("**Raw response:**\n\n```json\n")
                f.write(json.dumps(resp, indent=2)[:1500])
                f.write("\n```\n\n")
            f.write("**Observations:** _(filled in below)_\n\n---\n\n")
    print(f"\nWrote {args.out}")


if __name__ == "__main__":
    main()
