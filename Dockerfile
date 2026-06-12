FROM python:3.11-slim

# Non-root user (required by Hugging Face Spaces, good practice elsewhere).
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user PATH=/home/user/.local/bin:$PATH
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Pre-download the ONNX embedding model so first query isn't slow.
RUN python -c "from chromadb.utils.embedding_functions import ONNXMiniLM_L6_V2; ONNXMiniLM_L6_V2()(['warm up'])"

COPY --chown=user app/ app/
# The prebuilt Chroma index must exist (run scripts/build_index.py first).
COPY --chown=user data/chroma/ data/chroma/

# Hugging Face Spaces uses port 7860; Render/Railway inject $PORT.
ENV PORT=7860
EXPOSE 7860

CMD uvicorn app.main:app --host 0.0.0.0 --port ${PORT}
