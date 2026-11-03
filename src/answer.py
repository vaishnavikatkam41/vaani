"""Step 4 (baseline): build a grounded answer WITHOUT an LLM.

We pick the best sentences straight from the found passages.
Nothing is invented, so the answer is always grounded in a source.
"""
import re

from . import config
from .safety import split_sentences

STOPWORDS = {
    "the", "and", "for", "are", "with", "that", "this", "from", "have", "has", "what",
    "how", "should", "can", "does", "did", "when", "why", "who", "which", "will",
    "you", "your", "was", "were", "not", "but", "any", "all", "get", "give", "use",
    "about", "into", "than", "then", "them", "they", "there", "their", "also",
}


def keywords(text):
    return {w for w in re.findall(r"[a-zA-Z]{3,}", text.lower()) if w not in STOPWORDS}


def pick_sentences(question, hits, max_sentences=3, max_words=45):
    """Choose up to `max_sentences` sentences that share the most words with the question."""
    q_words = keywords(question)
    candidates = []  # (score, order, sentence)
    order = 0
    for hit in hits[:2]:
        for sentence in split_sentences(hit["text"]):
            if not 4 <= len(sentence.split()) <= max_words:
                continue
            overlap = len(q_words & keywords(sentence))
            if overlap:
                candidates.append((overlap, order, sentence))
            order += 1
    best = sorted(candidates, key=lambda c: (-c[0], c[1]))[:max_sentences]
    return " ".join(s for _, _, s in sorted(best, key=lambda c: c[1]))


def trust_level(score, retriever_kind):
    """Trust Meter (simple version): 'idk', 'unsure' or 'sure', from the retrieval score."""
    idk_below, sure_above = config.THRESHOLDS[retriever_kind]
    if score < idk_below:
        return "idk"
    if score < sure_above:
        return "unsure"
    return "sure"


TRUST_PREFIX = {
    "sure": {"en": "", "te": ""},
    "unsure": {
        "en": "I am not fully sure. Please confirm with an ASHA worker. ",
        "te": "నాకు పూర్తిగా ఖచ్చితంగా తెలియదు. దయచేసి ఆశా కార్యకర్తను అడగండి. ",
    },
}


def source_list(hits, limit=2):
    """Simple source names for the answer (no repeats)."""
    seen = []
    for h in hits:
        label = f"{h['source_name']}, page {h['page']}"
        if label not in seen:
            seen.append(label)
    return seen[:limit]
