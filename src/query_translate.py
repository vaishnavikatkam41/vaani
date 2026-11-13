"""Telugu question -> English search text.

Why? Our sources are English. Searching and reranking work much better when the
question is in the same language as the passages (eval: Telugu hit rate 59% -> 91%).

Two parts:
1. NLLB-200 (Meta, free, runs on this computer, no internet after the first download)
   translates the question.
2. A small health glossary (data/glossary_te_en.csv) adds the correct English term for
   words machine translation gets wrong, e.g. వడదెబ్బ was translated as "snowman" and
   ఆశా కార్యకర్త as "hopeful worker". Telugu speakers can add rows to that file.

The original Telugu question is still used too (see retrieval.py), so a bad
translation can never make search worse than before.
"""
import csv
import functools
import os

from . import config
from .translate import has_telugu

MODEL_NAME = os.getenv("VAANI_NLLB_MODEL", "facebook/nllb-200-distilled-600M")
GLOSSARY_FILE = config.ROOT / "data" / "glossary_te_en.csv"


@functools.lru_cache(maxsize=1)
def load_glossary(path=GLOSSARY_FILE):
    if not path.exists():
        return ()
    with open(path, newline="", encoding="utf-8") as f:
        return tuple((r["telugu"].strip(), r["english"].strip())
                     for r in csv.DictReader(f) if r.get("telugu") and r.get("english"))


def glossary_terms(text):
    """English terms for every glossary word found in the Telugu text (no repeats)."""
    seen = []
    for te, en in load_glossary():
        if te in text and en not in seen:
            seen.append(en)
    return seen


@functools.lru_cache(maxsize=1)
def _model():
    from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
    tok = AutoTokenizer.from_pretrained(MODEL_NAME, src_lang="tel_Telu")
    model = AutoModelForSeq2SeqLM.from_pretrained(MODEL_NAME)
    model.eval()
    return tok, model


@functools.lru_cache(maxsize=2048)
def machine_translate(text):
    """Telugu -> English with NLLB. Returns None if the model cannot be used."""
    if os.environ.get("VAANI_NO_NLLB"):
        return None
    try:
        tok, model = _model()
        ids = tok(text[:500], return_tensors="pt")
        out = model.generate(**ids, forced_bos_token_id=tok.convert_tokens_to_ids("eng_Latn"),
                             max_new_tokens=64, num_beams=2)
        return tok.batch_decode(out, skip_special_tokens=True)[0].strip() or None
    except Exception as error:  # library missing, download failed, ...
        print("Question translation unavailable:", error)
        return None


def to_english(text):
    """Return English search text for a Telugu question, or None for English questions.

    Glossary terms are added even if machine translation is unavailable, so search
    still gets the key English health words."""
    if not has_telugu(text):
        return None
    parts = []
    translated = machine_translate(text)
    if translated:
        parts.append(translated)
    terms = glossary_terms(text)
    if terms:
        parts.append("(" + "; ".join(terms) + ")")
    return " ".join(parts) or None
