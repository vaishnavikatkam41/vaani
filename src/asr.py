"""Step 1: speech to text (Telugu).

Order (first one that works is used):
  1. Sarvam AI (cloud, Telugu-trained)  - needs SARVAM_API_KEY. Best quality.
  2. A Telugu fine-tuned Whisper model  - free, runs on this computer.
     Default: see DEFAULT_LOCAL_MODEL. Change with VAANI_ASR_MODEL.
  3. faster-whisper "small" (general)   - last resort.

Why not a "hint" sentence any more? We used to give Whisper a Telugu hint
("పిల్లలకు జ్వరం వస్తే ఏం చేయాలి? ..."). When the audio was unclear, Whisper
COPIED words from the hint, so people saw a question they never asked.
Sarvam's `keyterms` is safer: it only nudges towards listed words.

Measured with tools/asr_benchmark.py (results in eval/asr_results.json).
"""
import os

DEFAULT_LOCAL_MODEL = "vasista22/whisper-telugu-small"
SARVAM_URL = "https://api.sarvam.ai/speech-to-text"

# Kept only so the benchmark can show the old behaviour. NOT used for real answers.
OLD_HINT = "ఇది తెలుగు ఆరోగ్య ప్రశ్న. పిల్లలకు జ్వరం వస్తే ఏం చేయాలి? విరేచనాలు, గర్భిణీ, నవజాత శిశువు."

# Words villagers are likely to say. Sarvam uses them as a gentle bias (max 50).
HEALTH_TERMS = [
    "జ్వరం", "విరేచనాలు", "వాంతులు", "దగ్గు", "జలుబు", "గర్భిణీ", "ప్రసవం", "నవజాత శిశువు",
    "తల్లిపాలు", "టీకా", "డెంగ్యూ", "మలేరియా", "దోమలు", "వడదెబ్బ", "కుక్క కాటు", "పాము కాటు",
    "రేబిస్", "బీపీ", "షుగర్", "మధుమేహం", "రక్తపోటు", "వృద్ధులు", "మానసిక ఆరోగ్యం", "ఒత్తిడి",
    "ఆశా కార్యకర్త", "ఆసుపత్రి", "ఛాతీ నొప్పి", "ఊపిరి", "రక్తస్రావం", "ఫిట్స్", "ఓఆర్ఎస్",
    "బొడ్డు తాడు", "పోషకాహారం", "రక్తహీనత", "చేతులు కడగడం", "తాగునీరు",
]

_local = None


def _sarvam(audio_path, key):
    """Telugu-trained cloud speech-to-text (Sarvam AI). The key stays on the server."""
    import json

    import httpx
    data = {"language_code": "te-IN", "model": os.getenv("SARVAM_MODEL", "saaras:v4")}
    if data["model"].startswith("saaras:v4"):
        data["keyterms"] = json.dumps(HEALTH_TERMS, ensure_ascii=False)
    with open(audio_path, "rb") as audio:
        reply = httpx.post(SARVAM_URL, headers={"api-subscription-key": key},
                           files={"file": (os.path.basename(audio_path), audio)},
                           data=data, timeout=60)
    if reply.status_code == 400 and "keyterms" in data:   # older account / model: retry plain
        data.pop("keyterms")
        with open(audio_path, "rb") as audio:
            reply = httpx.post(SARVAM_URL, headers={"api-subscription-key": key},
                               files={"file": (os.path.basename(audio_path), audio)},
                               data=data, timeout=60)
    reply.raise_for_status()
    return (reply.json().get("transcript") or "").strip()


class HFWhisper:
    """Any Whisper model from Hugging Face (e.g. a Telugu fine-tune), on CPU."""

    def __init__(self, model_name):
        import torch
        from transformers import pipeline
        torch.set_num_threads(max(1, (os.cpu_count() or 2) - 1))
        self.pipe = pipeline("automatic-speech-recognition", model=model_name, device="cpu")
        # Fine-tunes made with old library versions (2022) carry an outdated generation
        # config that new versions reject ("generation config is outdated"). Use the standard
        # multilingual Whisper config instead (the documented fix, transformers issue 25084).
        gen = self.pipe.model.generation_config
        if not getattr(gen, "lang_to_id", None):
            from transformers import GenerationConfig
            gen = GenerationConfig.from_pretrained("openai/whisper-small")
            self.pipe.model.generation_config = gen
        gen.forced_decoder_ids = None
        self.multilingual = True

    def transcribe(self, audio_path):
        from faster_whisper import decode_audio   # reads webm/mp3/wav/m4a -> 16 kHz mono
        audio = decode_audio(audio_path, sampling_rate=16000)
        kwargs = {"task": "transcribe", "max_new_tokens": 200}
        if self.multilingual:
            kwargs["language"] = "telugu"
        out = self.pipe({"raw": audio, "sampling_rate": 16000}, generate_kwargs=kwargs,
                        chunk_length_s=30)
        return (out.get("text") or "").strip()


def _local_transcribe(audio_path):
    global _local
    if _local is None:
        name = os.getenv("VAANI_ASR_MODEL", DEFAULT_LOCAL_MODEL)
        try:
            _local = HFWhisper(name).transcribe
        except Exception as error:   # model download failed / library missing
            print(f"Local Telugu model '{name}' unavailable ({error}); using Whisper small.")
            _local = _faster_whisper_small
    return _local(audio_path)


def _faster_whisper_small(audio_path):
    from faster_whisper import WhisperModel
    global _fw
    try:
        _fw
    except NameError:
        _fw = WhisperModel("small", device="cpu", compute_type="int8")
    segments, _info = _fw.transcribe(audio_path, language="te", vad_filter=True, beam_size=5,
                                     condition_on_previous_text=False)
    return " ".join(segment.text.strip() for segment in segments).strip()


def engine_name():
    """Which engine will be used (for the /health page and the setup checks)."""
    if os.getenv("SARVAM_API_KEY"):
        return "sarvam:" + os.getenv("SARVAM_MODEL", "saaras:v4")
    return "local:" + os.getenv("VAANI_ASR_MODEL", DEFAULT_LOCAL_MODEL)


def transcribe(audio_path, language="te"):
    key = os.getenv("SARVAM_API_KEY")
    if key:
        try:
            return _sarvam(audio_path, key)
        except Exception as error:   # no internet, wrong key, limit: use the local model
            print("Sarvam speech-to-text failed, using the local model:", error)
    return _local_transcribe(audio_path)
