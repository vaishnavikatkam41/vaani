"""OPTIONAL step 4: an LLM writes a short Telugu answer from the passages.

Without an API key, Vaani uses the simple extractive answer (English).
That is our BASELINE. When you add the key, compare the two in eval/.

Setup (Windows):
    pip install anthropic
    set ANTHROPIC_API_KEY=your_key_here
"""
import os

SYSTEM_PROMPT = """You are Vaani, a health awareness helper for people who cannot read well.
Rules you must never break:
1. Use ONLY the passages given. Do not use any other knowledge.
2. If the passages do not answer the question, reply with exactly: NO_ANSWER
3. Never diagnose. Never say "you have <disease>".
4. Never give medicine doses, tablet counts or mg amounts.
5. Write in simple spoken Telugu. Short sentences. One idea at a time. No jargon.
6. Maximum 5 sentences.
"""


def available():
    return bool(os.getenv("ANTHROPIC_API_KEY"))


def write_answer(question, passages):
    """Return the Telugu answer text, or None if the model says NO_ANSWER."""
    import anthropic  # imported here so the project runs without this library

    client = anthropic.Anthropic()
    context = "\n\n".join(f"[{i + 1}] {p['text']}" for i, p in enumerate(passages))
    reply = client.messages.create(
        model=os.getenv("VAANI_LLM_MODEL", "claude-haiku-5-5"),
        max_tokens=400,
        temperature=0,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user",
                   "content": f"Passages:\n{context}\n\nQuestion: {question}"}],
    )
    text = reply.content[0].text.strip()
    return None if "NO_ANSWER" in text else text
