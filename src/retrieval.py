"""Step 3 of the pipeline: find the passages that match the question.

Two retrievers:
1. TfidfRetriever  - simple BASELINE. Matches words. Works for English questions.
2. EmbeddingRetriever - matches MEANING and works across languages (Telugu question,
   English document). Needs: pip install sentence-transformers faiss-cpu

Why a baseline first? So we can show in interviews that the better method
really improved the numbers.
"""
from . import config
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel


class TfidfRetriever:
    kind = "tfidf"

    def __init__(self, chunks):
        self.chunks = chunks
        self.vectorizer = TfidfVectorizer(
            stop_words="english", ngram_range=(1, 2), sublinear_tf=True
        )
        self.matrix = self.vectorizer.fit_transform([c["text"] for c in chunks])

    def search(self, query, k=3):
        """Return the top k chunks, each with a 'score' between 0 and 1."""
        query_vec = self.vectorizer.transform([query])
        scores = linear_kernel(query_vec, self.matrix).ravel()
        best = scores.argsort()[::-1][:k]
        return [dict(self.chunks[i], score=float(scores[i])) for i in best]


class EmbeddingRetriever:
    kind = "embedding"

    def __init__(self, chunks, model_name="intfloat/multilingual-e5-small"):
        # Imported here so the project still runs without these big libraries.
        import hashlib

        import faiss
        import numpy as np
        from sentence_transformers import SentenceTransformer

        self.np = np
        self.chunks = chunks
        self.model = SentenceTransformer(model_name)
        self.model.max_seq_length = 256   # our chunks are short; a lower limit is faster

        # Making the numbers for 3000 chunks is SLOW (many minutes on a laptop).
        # So we save them once in data/cache and reuse them while the chunks stay the same.
        key = hashlib.sha256(
            (model_name + "\n".join(c["text"] for c in chunks)).encode("utf-8")
        ).hexdigest()[:16]
        cache_file = config.ROOT / "data" / "cache" / f"embeddings_{key}.npy"

        if cache_file.exists():
            print("Using saved embeddings (fast).", flush=True)
            vectors = np.load(cache_file)
        else:
            print("Making embeddings once. This is slow, but only the first time.", flush=True)
            # e5 models need these two prefixes. Without them, quality drops.
            vectors = self.model.encode(
                ["passage: " + c["text"] for c in chunks],
                normalize_embeddings=True, show_progress_bar=True, batch_size=16,
            )
            cache_file.parent.mkdir(parents=True, exist_ok=True)
            np.save(cache_file, vectors)

        self.index = faiss.IndexFlatIP(vectors.shape[1])  # inner product = cosine
        self.index.add(np.asarray(vectors, dtype="float32"))

    def search(self, query, k=3):
        q = self.model.encode(["query: " + query], normalize_embeddings=True)
        scores, ids = self.index.search(self.np.asarray(q, dtype="float32"), k)
        return [dict(self.chunks[i], score=float(s))
                for s, i in zip(scores[0], ids[0]) if i != -1]


def get_retriever(kind, chunks):
    if kind == "embedding":
        return EmbeddingRetriever(chunks)
    return TfidfRetriever(chunks)
