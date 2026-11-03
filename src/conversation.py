"""Short memory for ONE conversation.

- Kept only in RAM. Nothing is written to disk.
- Deleted when the user closes the app (/end) or after 30 minutes.
- No login, so we never know who the user is. This protects privacy.
"""
import time
import uuid

from . import config


class SessionStore:
    def __init__(self):
        self._sessions = {}

    def new_id(self):
        return uuid.uuid4().hex

    def _purge(self):
        now = time.time()
        old = [sid for sid, s in self._sessions.items()
               if now - s["last_seen"] > config.SESSION_TTL_SECONDS]
        for sid in old:
            del self._sessions[sid]

    def previous_question(self, session_id):
        """Return the user's last question in this conversation, or ''."""
        self._purge()
        session = self._sessions.get(session_id)
        if not session or not session["turns"]:
            return ""
        return session["turns"][-1]["question"]

    def add_turn(self, session_id, question, answer):
        self._purge()
        session = self._sessions.setdefault(
            session_id, {"turns": [], "last_seen": time.time()})
        session["turns"].append({"question": question, "answer": answer})
        session["turns"] = session["turns"][-config.SESSION_MAX_TURNS:]
        session["last_seen"] = time.time()

    def end(self, session_id):
        self._sessions.pop(session_id, None)
