# Backend image for a Hugging Face Docker Space (free CPU: 2 vCPU, 16 GB RAM). See README "Deploy".
# The Space repo is filled by `python scripts/deploy_space.py`, which copies this file, the code,
# the committed chunks and the prebuilt vector index (data/qdrant); nothing is indexed at startup.
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    HF_HOME=/home/user/hf_cache \
    PORT=7860

# Spaces run the container as uid 1000.
RUN useradd -m -u 1000 user
WORKDIR /home/user/app

# CPU-only PyTorch (~200 MB instead of ~2 GB of CUDA wheels). Override for a local build where
# the PyTorch index is unreachable: --build-arg TORCH_INDEX=https://pypi.org/simple
ARG TORCH_INDEX=https://download.pytorch.org/whl/cpu
RUN pip install torch --index-url ${TORCH_INDEX}

COPY --chown=user pyproject.toml README.md ./
COPY --chown=user backend backend
COPY --chown=user ingestion ingestion
COPY --chown=user eval eval
RUN pip install ".[ml]"

USER user
# Bake both models into the image (~3.5 GB) so a sleeping Space wakes without downloading them.
# Loading the reranker once also caches gte's pinned remote model code (D62).
RUN python -c "from huggingface_hub import snapshot_download as d; d('BAAI/bge-m3'); \
from backend.app.config import get_settings; from backend.app.rag.reranker import make_reranker; \
make_reranker(get_settings())"

COPY --chown=user data data

EXPOSE 7860
CMD ["sh", "-c", "uvicorn backend.app.main:app --host 0.0.0.0 --port ${PORT}"]
