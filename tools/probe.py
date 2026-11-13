"""Shows how well Telugu and English questions match the documents.
Run:  py tools\\probe.py
It changes nothing. It only prints scores so we can pick fair limits."""
import io
import sys

from src import config
from src.pipeline import Vaani

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# (label, Telugu question, English question)  -- these SHOULD be answered
ON_TOPIC = [
    ("fever",     "పిల్లలకు జ్వరం వస్తే ఏం చేయాలి?",           "What should I do if my child has fever?"),
    ("diarrhoea", "పిల్లలకు విరేచనాలు అయితే ఏం చేయాలి?",        "What should I do if my child has diarrhoea?"),
    ("pregnancy", "గర్భిణీ స్త్రీ ఎలా జాగ్రత్తగా ఉండాలి?",       "How should a pregnant woman take care of herself?"),
    ("newborn",   "నవజాత శిశువును ఎలా చూసుకోవాలి?",             "How should I care for a newborn baby?"),
    ("burns",     "కాలిన గాయానికి ప్రథమ చికిత్స ఏమిటి?",        "What is first aid for a burn?"),
    ("bp",        "రక్తపోటు తగ్గించుకోవడానికి ఏం చేయాలి?",       "What can I do to lower blood pressure?"),
]
# These should NOT be answered
OFF_TOPIC = [
    ("crop",   "వరి పంటకు ఏ ఎరువు వేయాలి?",        "Which fertiliser should I use for paddy?"),
    ("movie",  "ఈ వారం ఏ సినిమా విడుదల అవుతుంది?",  "Which movie releases this week?"),
    ("share",  "ఏ షేర్లు కొనాలి?",                  "Which shares should I buy?"),
]

v = Vaani(retriever_kind="embedding", log_unanswered=False)
print("search kind:", v.kind, "| limits (idk, unsure):", config.THRESHOLDS.get(v.kind))


def score(q):
    hits = v.retriever.search(q, k=config.TOP_K)
    return hits[0]["score"] if hits else 0.0


def show(title, rows):
    print("\n" + title)
    print(f"{'topic':10} {'Telugu':>8} {'English':>8}")
    out = []
    for label, te, en in rows:
        s_te, s_en = score(te), score(en)
        out.append((s_te, s_en))
        print(f"{label:10} {s_te:8.3f} {s_en:8.3f}")
    return out


on = show("SHOULD ANSWER", ON_TOPIC)
off = show("SHOULD NOT ANSWER", OFF_TOPIC)
print("\nlowest Telugu on-topic :", round(min(a for a, _ in on), 3))
print("highest Telugu off-topic:", round(max(a for a, _ in off), 3))
