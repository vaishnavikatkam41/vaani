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


def _whole_sentences(text, max_words):
    """Sentences of a passage, without the half-sentence a chunk often starts with
    (chunks are cut by word count, so the first piece may begin mid-sentence)."""
    out = []
    for i, sentence in enumerate(split_sentences(text)):
        if i == 0 and sentence[:1].islower():
            continue
        if 4 <= len(sentence.split()) <= max_words:
            out.append(sentence)
    return out


def pick_sentences(question, hits, max_sentences=3, max_words=45):
    """Choose up to `max_sentences` sentences that share the most words with the question.
    For a Telugu question we match on the English search text the retriever made."""
    q_words = keywords(question)
    if not q_words and hits and hits[0].get("search_text"):
        q_words = keywords(hits[0]["search_text"])
    candidates = []  # (score, order, sentence)
    order = 0
    for hit in hits[:2]:
        for sentence in _whole_sentences(hit["text"], max_words):
            overlap = len(q_words & keywords(sentence))
            if overlap:
                candidates.append((overlap, order, sentence))
            order += 1
    if not candidates and hits:
        # No shared words (a Telugu question has no English words to match).
        # Retrieval already found the best passage by MEANING, so use its first sentences.
        first = _whole_sentences(hits[0]["text"], max_words) or [
            x for x in split_sentences(hits[0]["text"]) if 4 <= len(x.split()) <= max_words]
        return " ".join(first[:max_sentences])
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
