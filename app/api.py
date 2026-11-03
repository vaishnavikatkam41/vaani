"""The server the mobile app will talk to. (No login. No user data saved.)

Run:  py -m uvicorn app.api:app --reload
Then open: http://127.0.0.1:8000/docs  (a free test page made by FastAPI)
"""
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel

from src.pipeline import Vaani

app = FastAPI(title="Vaani API", version="0.1")

AUDIO_DIR = Path(tempfile.gettempdir()) / "vaani_audio"
AUDIO_DIR.mkdir(exist_ok=True)

_vaani = None


def get_vaani():
    """Load the brain once, on first use."""
    global _vaani
    if _vaani is None:
        _vaani = Vaani()
    return _vaani


class AskRequest(BaseModel):
    text: str
    session_id: str | None = None   # app sends the same id during one conversation


class EndRequest(BaseModel):
    session_id: str


@app.get("/health")
def health():
    return {"ok": True}


@app.post("/ask")
def ask(req: AskRequest):
    session_id = req.session_id or get_vaani().sessions.new_id()
    result = get_vaani().ask(req.text, session_id=session_id)
    return {**result, "session_id": session_id}


@app.post("/end")
def end(req: EndRequest):
    """App calls this when the user closes it. The conversation is forgotten."""
    get_vaani().end(req.session_id)
    return {"ended": True}


@app.post("/ask_voice")
async def ask_voice(session_id: str | None = None, audio: UploadFile = File(...)):
    """Voice in -> voice out. Needs: faster-whisper and gTTS (see requirements-voice.txt)."""
    from src import asr, tts

    suffix = Path(audio.filename or "q.wav").suffix or ".wav"
    in_path = AUDIO_DIR / f"{uuid.uuid4().hex}{suffix}"
    in_path.write_bytes(await audio.read())
    try:
        transcript = asr.transcribe(str(in_path))
    finally:
        in_path.unlink(missing_ok=True)   # do not keep people's voices

    session_id = session_id or get_vaani().sessions.new_id()
    result = get_vaani().ask(transcript, session_id=session_id)
    audio_name = f"{uuid.uuid4().hex}.mp3"
    tts.speak(result["answer"], AUDIO_DIR / audio_name, lang=result["language"])
    return {**result, "transcript": transcript, "session_id": session_id,
            "audio_url": f"/audio/{audio_name}"}


@app.get("/audio/{name}")
def get_audio(name: str):
    path = AUDIO_DIR / Path(name).name   # Path(...).name stops "../" tricks
    if not path.exists():
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(path, media_type="audio/mpeg")
