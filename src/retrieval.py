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


class RerankRetriever:
    """Best search (default). Three steps:

    1. Telugu question -> English search text (NLLB + health glossary, query_translate.py).
    2. Embedding search with BOTH the original and the English text; keep the
       best `candidates` passages from the union (cheap, finds possible matches).
    3. A cross-encoder (bge-reranker-v2-m3) reads question + passage TOGETHER and
       scores how well the passage answers it (slower, much more accurate).

    Why step 3? With embeddings alone, off-topic questions ("how do I learn English?")
    scored 0.84 and real Telugu health questions 0.80 - no safe cut-off existed.
    Reranker scores put off-topic near 0.00 and real questions far above, so the
    "I don't know" gate has a wide safety margin. Score = reranker score (0..1).
    """
    kind = "rerank"

    def __init__(self, chunks, candidates=10, model_name="BAAI/bge-reranker-v2-m3",
                 embedder=None):
        from sentence_transformers import CrossEncoder

        self.chunks = chunks
        self.candidates = candidates
        self.embedder = embedder or EmbeddingRetriever(chunks)
        self.reranker = CrossEncoder(model_name, max_length=256)
        self._cache = {}

    def search(self, query, k=3):
        if query in self._cache:
            return self._cache[query][:k]
        from .query_translate import to_english

        english = to_english(query)
        pool = {}
        for text in filter(None, (query, english)):
            for hit in self.embedder.search(text, k=self.candidates):
                key = hit.get("id", hit["text"])
                if key not in pool or hit["score"] > pool[key]["embed_score"]:
                    pool[key] = dict(hit, embed_score=hit["score"])
        if not pool:
            return []
        hits = list(pool.values())
        rerank_text = english or query
        scores = self.reranker.predict([(rerank_text, h["text"]) for h in hits])
        for hit, score in zip(hits, scores):
            hit["score"] = float(score)
            hit["search_text"] = rerank_text
        hits.sort(key=lambda h: -h["score"])
        if len(self._cache) > 512:
            self._cache.clear()
        self._cache[query] = hits
        return hits[:k]


def get_retriever(kind, chunks):
    if kind == "rerank":
        return RerankRetriever(chunks)
    if kind == "embedding":
        return EmbeddingRetriever(chunks)
    return TfidfRetriever(chunks)
