"""Safety layer. This file protects the user. Read it twice before changing it.

Three jobs:
1. Emergency Fast Lane - catch danger words BEFORE anything else.
2. Dose requests       - Vaani never gives medicine doses.
3. Answer filter       - remove any sentence with a dose or a diagnosis.

IMPORTANT: The Telugu word lists below are a STARTING LIST. Ask a Telugu
speaker, an ASHA worker or a nurse to review and add Telangana, Coastal Andhra
and Rayalaseema forms. Recall (never missing an emergency) matters most.
"""
import re

# ---------- 1. Emergency words ----------
EMERGENCY_WORDS = [
    # English
    "chest pain", "heart attack", "can't breathe", "cant breathe", "cannot breathe",
    "difficulty breathing", "not breathing", "short of breath", "heavy bleeding",
    "bleeding a lot", "bleeding will not stop", "bleeding won't stop", "fits",
    "seizure", "convulsion", "snake", "snake bite", "snakebite", "bitten by a snake",
    "unconscious", "not waking up", "fainted", "poison", "poisoning", "swallowed pesticide",
    "drank pesticide", "baby not moving", "high fever with stiff neck",
    # Telugu (Telugu script)
    "ఛాతీ నొప్పి", "ఛాతిలో నొప్పి", "గుండె నొప్పి", "గుండెపోటు",
    "ఊపిరి ఆడ", "ఊపిరాడ", "శ్వాస తీసుకోలేక", "శ్వాస ఆడ",
    "రక్తస్రావం", "రక్తం ఆగడం లేదు", "రక్తం ఆగట్లేదు", "ఎక్కువ రక్తం",
    "ఫిట్స్", "మూర్ఛ", "ఫిట్",
    "పాము కాటు", "పాము కరిచ", "పాము కరి",
    "స్పృహ తప్ప", "స్పృహ లేదు", "కళ్లు తిరిగి పడ", "కళ్ళు తిరిగి పడ", "లేవడం లేదు",
    "విషం తాగ", "పురుగుల మందు తాగ", "పురుగు మందు తాగ",
]

# Mental-health crisis words. Different answer: call Tele-MANAS 14416 or 108.
CRISIS_WORDS = [
    "suicide", "kill myself", "want to die", "end my life",
    "ఆత్మహత్య", "చచ్చిపోవాలని", "చనిపోవాలని", "చావాలని",
]

# ---------- 2. Dose requests ----------
DOSE_REQUEST_PATTERNS = [
    r"\bdose\b", r"\bdosage\b", r"\bhow (many|much) (tablets?|pills?|mg|ml|drops?)\b",
    r"\bhow many times a day\b", r"\bwhich (tablet|medicine|medication|antibiotic)\b",
    r"మోతాదు", r"ఏ మాత్ర", r"ఎన్ని మాత్రలు", r"ఏ మందు",
]

# ---------- 3. Answer filter ----------
# We block MEDICINE amounts (mg, tablets, drops...). We still allow
# ORS / water amounts (ml, glass, litre) because those are home-care guidance.
# Talk to your mentor before changing this rule.
DOSE_IN_ANSWER = re.compile(
    r"(\b\d+(\.\d+)?\s*(mg|mcg|µg|ug|iu|g|gm|gms)\b)"
    r"|(\b\d+\s*[-–]?\s*(tablets?|tabs?|capsules?|pills?|drops?|teaspoons?|tsp)\b)"
    r"|(\b(dose|doses|dosage|dosing|syrup|injection)\b)"
    r"|(మోతాదు)|(మి\.గ్రా)|(మిల్లీగ్రాము)",
    re.IGNORECASE,
)
DIAGNOSIS_IN_ANSWER = re.compile(
    r"\b(you|your (child|baby|mother|father))\s+(have|has|are suffering from|is suffering from|"
    r"might have|may have|probably have|definitely have)\b",
    re.IGNORECASE,
)

# ---------- Messages (Telugu first, English second) ----------
MESSAGES = {
    "emergency": {
        "te": "ఇది అత్యవసరం. వెంటనే ఆసుపత్రికి వెళ్లండి. 108 కు కాల్ చేయండి.",
        "en": "This is an emergency. Go to the hospital now. Call 108.",
    },
    "crisis": {
        "te": "మీరు ఒంటరి కాదు. వెంటనే 14416 కు కాల్ చేయండి, లేదా 108 కు కాల్ చేయండి. మీ దగ్గరి వ్యక్తికి చెప్పండి.",
        "en": "You are not alone. Call 14416 now, or call 108. Tell someone near you.",
    },
    "idk": {
        "te": "నాకు తెలియదు. దయచేసి డాక్టర్‌ను లేదా ఆశా కార్యకర్తను అడగండి.",
        "en": "I don't know. Please ask a doctor or an ASHA worker.",
    },
    "refuse": {
        "te": "నేను మందుల మోతాదు చెప్పలేను. దయచేసి డాక్టర్‌ను, ఫార్మసిస్ట్‌ను లేదా ఆశా కార్యకర్తను అడగండి.",
        "en": "I cannot tell medicine doses. Please ask a doctor, a pharmacist or an ASHA worker.",
    },
}


def _contains_any(text, words):
    """English words must match as whole words ('fits' must not match 'benefits').
    Telugu has no simple word edges, so Telugu phrases match anywhere in the text."""
    text = text.lower().replace("’", "'")
    for word in words:
        word = word.lower()
        if word.isascii():
            if re.search(r"(?<![a-z])" + re.escape(word) + r"(?![a-z])", text):
                return True
        elif word in text:
            return True
    return False


def check_emergency(text):
    """Return 'emergency', 'crisis' or None. Crisis is checked first."""
    if _contains_any(text, CRISIS_WORDS):
        return "crisis"
    if _contains_any(text, EMERGENCY_WORDS):
        return "emergency"
    return None


def is_dose_request(text):
    return any(re.search(p, text, re.IGNORECASE) for p in DOSE_REQUEST_PATTERNS)


def split_sentences(text):
    return [s.strip() for s in re.split(r"(?<=[.!?।])\s+", text) if s.strip()]


def find_violations(text):
    """Return a list of problems found in an answer sentence (empty = safe)."""
    problems = []
    if DOSE_IN_ANSWER.search(text):
        problems.append("dose")
    if DIAGNOSIS_IN_ANSWER.search(text):
        problems.append("diagnosis")
    return problems


def filter_answer(text):
    """Remove every unsafe sentence. Returns (safe_text, number_removed).
    If safe_text is empty, the pipeline must refuse to answer."""
    safe, removed = [], 0
    for sentence in split_sentences(text):
        if find_violations(sentence):
            removed += 1
        else:
            safe.append(sentence)
    return " ".join(safe), removed
