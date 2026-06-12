"""Deploy the app (with prebuilt index) to a Hugging Face Space (Docker SDK).

Prereqs: `hf auth login` done, index built at data/chroma, GROQ_API_KEY in env/.env.
Usage:  python scripts/deploy_hf.py [--space-id user/python-qa-assistant]
"""
import argparse
import os
from pathlib import Path

from dotenv import load_dotenv
from huggingface_hub import HfApi

BASE_DIR = Path(__file__).resolve().parent.parent

SPACE_README = """\
---
title: Python Programming Q&A Assistant
emoji: 🐍
colorFrom: green
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# Python Programming Q&A Assistant

RAG-powered Q&A over the Stack Overflow Python dataset. FastAPI + ChromaDB +
Llama 3.1 (Groq). POST /ask with {"question": "..."} or open /docs.
"""


def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    api = HfApi()
    user = api.whoami()["name"]

    parser = argparse.ArgumentParser()
    parser.add_argument("--space-id", default=f"{user}/python-qa-assistant")
    args = parser.parse_args()
    space_id = args.space_id

    api.create_repo(space_id, repo_type="space", space_sdk="docker", exist_ok=True)
    api.add_space_secret(space_id, "GROQ_API_KEY", os.environ["GROQ_API_KEY"])
    api.add_space_variable(space_id, "GROQ_MODEL",
                           os.getenv("GROQ_MODEL", "llama-3.1-8b-instant"))

    api.upload_file(path_or_fileobj=SPACE_README.encode(), path_in_repo="README.md",
                    repo_id=space_id, repo_type="space")
    for f in ["Dockerfile", "requirements.txt"]:
        api.upload_file(path_or_fileobj=BASE_DIR / f, path_in_repo=f,
                        repo_id=space_id, repo_type="space")
    api.upload_folder(folder_path=BASE_DIR / "app", path_in_repo="app",
                      repo_id=space_id, repo_type="space")
    api.upload_folder(folder_path=BASE_DIR / "data" / "chroma",
                      path_in_repo="data/chroma",
                      repo_id=space_id, repo_type="space")

    print(f"Deployed: https://huggingface.co/spaces/{space_id}")
    print(f"API URL:  https://{space_id.replace('/', '-').replace('_', '-')}.hf.space")


if __name__ == "__main__":
    main()
