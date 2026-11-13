# Used by Hugging Face Spaces (free, 16 GB RAM). Built from the folder made by deploy/make_space.py
FROM python:3.11-slim

# faiss needs this small system library
USER root
RUN apt-get update && apt-get install -y --no-install-recommends libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Spaces runs the app as user 1000
RUN useradd -m -u 1000 user
USER user
ENV PATH="/home/user/.local/bin:$PATH" \
    HF_HOME=/home/user/.cache/huggingface \
    PYTHONUNBUFFERED=1
WORKDIR /home/user/app

COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Download the models while building, so the first visitor does not wait
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('intfloat/multilingual-e5-small')"
RUN python -c "from faster_whisper import WhisperModel; WhisperModel('small', device='cpu', compute_type='int8')"
# Reranker (relevance gate) and NLLB (Telugu question -> English search text)
RUN python -c "from sentence_transformers import CrossEncoder; CrossEncoder('BAAI/bge-reranker-v2-m3')"
RUN python -c "from transformers import AutoTokenizer, AutoModelForSeq2SeqLM as M; n='facebook/nllb-200-distilled-600M'; AutoTokenizer.from_pretrained(n); M.from_pretrained(n)"

COPY --chown=user . .
EXPOSE 7860
CMD ["uvicorn", "app.api:app", "--host", "0.0.0.0", "--port", "7860"]
