"""Step 1: speech to text (Telugu).

Install: pip install faster-whisper
First run downloads the model (small = about 500 MB).

Honest note: base Whisper is weak in Telugu. Measure the Word Error Rate (WER)
first. If it is bad, try a bigger model (VAANI_ASR_MODEL=medium) or a Telugu
fine-tuned Whisper model from Hugging Face.
"""
import os

_model = None

# A short Telugu sentence. It nudges Whisper to write Telugu letters (not Hindi) and
# to expect health words. It is a hint only, not an answer.
HINT = "ఇది తెలుగు ఆరోగ్య ప్రశ్న. పిల్లలకు జ్వరం వస్తే ఏం చేయాలి? విరేచనాలు, గర్భిణీ, నవజాత శిశువు."


def _sarvam(audio_path, key):
    """Telugu-trained cloud speech-to-text (Sarvam AI). The key stays on the server."""
    import httpx
    data = {"language_code": "te-IN"}
    if os.getenv("SARVAM_MODEL"):
        data["model"] = os.getenv("SARVAM_MODEL")
    with open(audio_path, "rb") as audio:
        reply = httpx.post("https://api.sarvam.ai/speech-to-text",
                           headers={"api-subscription-key": key},
                           files={"file": (os.path.basename(audio_path), audio)},
                           data=data, timeout=60)
    reply.raise_for_status()
    return (reply.json().get("transcript") or "").strip()


def transcribe(audio_path, language="te"):
    key = os.getenv("SARVAM_API_KEY")
    if key:
        try:
            return _sarvam(audio_path, key)
        except Exception as error:   # no internet, wrong key, limit: use our own Whisper
            print("Sarvam speech-to-text failed, using Whisper:", error)
    return _whisper(audio_path, language)


def _whisper(audio_path, language="te"):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        size = os.getenv("VAANI_ASR_MODEL", "small")
        _model = WhisperModel(size, device="cpu", compute_type="int8")
    segments, _info = _model.transcribe(
        audio_path, language=language, vad_filter=True, beam_size=5,
        initial_prompt=HINT, condition_on_previous_text=False)
    return " ".join(segment.text.strip() for segment in segments).strip()
