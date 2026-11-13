"""The server the app talks to. (No login. No user data saved.)

Run:  py -m uvicorn app.api:app
Then open: http://127.0.0.1:8000        (the app page)
           http://127.0.0.1:8000/docs   (a free test page made by FastAPI)
"""
import os
import secrets
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from src import db
from src.pipeline import Vaani

app = FastAPI(title="Vaani API", version="0.3")

AUDIO_DIR = Path(tempfile.gettempdir()) / "vaani_audio"
AUDIO_DIR.mkdir(exist_ok=True)
STATIC_DIR = Path(__file__).parent / "static"

_vaani = None


def get_vaani():
    """Load the brain once, on first use.
    Telugu questions need the meaning-based search, so 'embedding' is the default."""
    global _vaani
    if _vaani is None:
        kind = os.getenv("VAANI_RETRIEVER", "embedding")
        try:
            _vaani = Vaani(retriever_kind=kind)
        except ImportError:
            print("Embedding libraries missing. Using the simple word search instead.")
            _vaani = Vaani(retriever_kind="tfidf")
    return _vaani


class AskRequest(BaseModel):
    text: str
    session_id: str | None = None   # app sends the same id during one conversation
    speak: bool = False             # True = also make a spoken answer (audio_url)


class FeedbackRequest(BaseModel):
    helpful: bool
    status: str | None = None
    trust: str | None = None
    score: float | None = None
    question: str | None = None
    answer: str | None = None
    sources: list[str] | None = None


class EndRequest(BaseModel):
    session_id: str


@app.get("/health")
def health():
    return {"ok": True}


def make_audio(result):
    """Speak the answer. Returns the audio url, or None if text-to-speech is unavailable."""
    from src import tts
    try:
        name = f"{uuid.uuid4().hex}.mp3"
        tts.speak(result["answer"], AUDIO_DIR / name, lang=result["language"])
        return f"/audio/{name}"
    except Exception as error:   # no internet for gTTS etc.: the app still shows the text
        print("Text to speech failed:", error)
        return None


@app.post("/ask")
def ask(req: AskRequest):
    session_id = req.session_id or get_vaani().sessions.new_id()
    result = get_vaani().ask(req.text, session_id=session_id)
    audio_url = make_audio(result) if req.speak else None
    return {**result, "session_id": session_id, "audio_url": audio_url}


@app.post("/feedback")
def feedback(req: FeedbackRequest):
    """Thumbs up / down. No login, no ids. Text is saved only for thumbs down."""
    db.add_feedback(req.helpful, req.status, req.trust, req.score,
                    req.question, req.answer, req.sources)
    return {"saved": True}


@app.get("/stats")
def stats():
    """Counts only. No question text."""
    return db.stats()


@app.get("/admin/unanswered")
def admin_unanswered(x_admin_token: str | None = Header(default=None)):
    """For you and the ASHA reviewers. Set VAANI_ADMIN_TOKEN to turn this on."""
    token = os.getenv("VAANI_ADMIN_TOKEN")
    if not token or not x_admin_token or not secrets.compare_digest(token, x_admin_token):
        raise HTTPException(status_code=403, detail="not allowed")
    return {"unanswered": db.list_unanswered(), "not_helpful": db.list_not_helpful()}


@app.post("/end")
def end(req: EndRequest):
    """App calls this when the user closes it. The conversation is forgotten."""
    get_vaani().end(req.session_id)
    return {"ended": True}


@app.post("/ask_voice")
async def ask_voice(session_id: str | None = None, audio: UploadFile = File(...)):
    """Voice in -> voice out. Needs: faster-whisper, gTTS, deep-translator."""
    from src import asr

    suffix = Path(audio.filename or "q.webm").suffix or ".webm"
    in_path = AUDIO_DIR / f"{uuid.uuid4().hex}{suffix}"
    in_path.write_bytes(await audio.read())
    try:
        transcript = asr.transcribe(str(in_path))
    finally:
        in_path.unlink(missing_ok=True)   # do not keep people's voices

    session_id = session_id or get_vaani().sessions.new_id()
    result = get_vaani().ask(transcript, session_id=session_id)

    audio_url = make_audio(result)
    return {**result, "transcript": transcript, "session_id": session_id,
            "audio_url": audio_url}


@app.get("/audio/{name}")
def get_audio(name: str):
    path = AUDIO_DIR / Path(name).name   # Path(...).name stops "../" tricks
    if not path.exists():
        raise HTTPException(status_code=404, detail="audio not found")
    return FileResponse(path, media_type="audio/mpeg")


# The app page. Must come LAST so it does not hide the routes above.
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="app")
