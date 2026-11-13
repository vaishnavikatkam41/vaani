"""Step 4: an AI model writes a short answer from the found passages ONLY.

Provider: Sarvam AI -> set SARVAM_API_KEY (made for Indian languages, free credit at signup).
With no key, Vaani uses the simple extractive answer. That is our BASELINE.

The AI never sees anything except the question and the passages.
If the passages do not answer the question it must reply NO_ANSWER, and Vaani says
"I don't know". The safety filter (safety.py) still runs on whatever the AI writes.
"""
import os

SYSTEM_PROMPT = """You are Vaani, a health awareness helper for people who cannot read well.
Rules you must never break:
1. Use ONLY the passages given. Do not use any other knowledge.
2. If the passages do not clearly answer the question, reply with exactly: NO_ANSWER
3. Never diagnose. Never say "you have <disease>".
4. Never give medicine doses, tablet counts or mg amounts.
5. If the person describes danger (not breathing, heavy bleeding, fits, chest pain), tell them to go to the hospital and call 108.
6. Write in simple spoken language. Short sentences. One idea at a time. No jargon.
7. Maximum 5 short sentences. No bullet points, no markdown, no numbering.
8. Answer in the same language as the question. If the question is in Telugu, answer in Telugu script.
"""

SARVAM_URL = "https://api.sarvam.ai/v1/chat/completions"


def provider():
    if os.getenv("SARVAM_API_KEY"):
        return "sarvam"
    return None


def available():
    return provider() is not None


def _context(passages):
    return "\n\n".join(f"[{i + 1}] {p['text']}" for i, p in enumerate(passages))


def _sarvam(question, passages):
    import httpx
    reply = httpx.post(
        SARVAM_URL,
        headers={"api-subscription-key": os.environ["SARVAM_API_KEY"]},
        json={
            "model": os.getenv("SARVAM_LLM_MODEL", "sarvam-105b"),
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Passages:\n{_context(passages)}\n\nQuestion: {question}"},
            ],
            "temperature": 0.1,
            "max_tokens": 600,
            "reasoning_effort": None,   # no hidden "thinking": faster and cheaper
        },
        timeout=60,
    )
    reply.raise_for_status()
    return (reply.json()["choices"][0]["message"]["content"] or "").strip()


def write_answer(question, passages):
    """Return the answer text, or None if the model says NO_ANSWER.
    Raises an error if the provider fails (the caller falls back to the baseline)."""
    which = provider()
    if which == "sarvam":
        text = _sarvam(question, passages)
    else:
        raise RuntimeError("no LLM key set")
    if not text or "NO_ANSWER" in text:
        return None
    return text
