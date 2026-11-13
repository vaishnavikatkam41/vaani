"""Step 1: speech to text (Telugu).

Install: pip install faster-whisper
First run downloads the model (small = about 500 MB).

Honest note: base Whisper is weak in Telugu. Measure the Word Error Rate (WER)
first. If it is bad, try a bigger model (VAANI_ASR_MODEL=medium) or a Telugu
fine-tuned Whisper model from Hugging Face.
"""
import os

_model = None


def transcribe(audio_path, language="te"):
    global _model
    if _model is None:
        from faster_whisper import WhisperModel
        size = os.getenv("VAANI_ASR_MODEL", "small")
        _model = WhisperModel(size, device="cpu", compute_type="int8")
    segments, _info = _model.transcribe(audio_path, language=language, vad_filter=True)
    return " ".join(segment.text.strip() for segment in segments).strip()
