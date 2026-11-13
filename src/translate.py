"""English answer -> Telugu, for Telugu-speaking users.

Our sources are in English. If the user asked in Telugu, we translate the
(already safety-checked) English answer.

Install: pip install deep-translator   (free, needs internet, no key)

HONEST WARNING: machine translation can change the meaning of health advice.
This is a stop-gap. Later, an LLM (src/llm.py) writes the Telugu answer directly
from the passages, and a Telugu speaker or ASHA worker must review the answers.
"""
import os
import re

TELUGU_CHARS = re.compile(r"[ఀ-౿]")


def has_telugu(text):
    return bool(TELUGU_CHARS.search(text or ""))


def to_telugu(text):
    """Return the Telugu text, or None if translation fails (then we keep English)."""
    if os.environ.get("VAANI_NO_TRANSLATE"):   # set by eval: scores do not depend on it
        return None
    try:
        from deep_translator import GoogleTranslator
        out = GoogleTranslator(source="en", target="te").translate(text[:4500])
        return out.strip() if out else None
    except Exception as error:
        print("Translation failed, using English:", error)
        return None
