"""Tiny database for improving Vaani. SQLite = a single file, no setup.

WHAT IS SAVED (and what is not)
- unanswered : the text of a question when Vaani said "I don't know".
               Used to decide which sources to add (the Unanswered-Question Log).
- feedback   : thumbs up / down. A thumbs UP saves only counts (no text).
               A thumbs DOWN also saves the question and answer, so a nurse or
               ASHA worker can review what went wrong.
NEVER SAVED: conversations, voice recordings, names, phone numbers, device ids.

Free hosting note: on a free Hugging Face Space the disk is wiped on restart,
so this file resets. For permanent data, move to a free hosted database later.
"""
import os
import sqlite3
import threading
import time
from contextlib import closing
from pathlib import Path

from . import config

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS unanswered (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    question TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS feedback (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    helpful INTEGER NOT NULL,
    status TEXT,
    trust TEXT,
    score REAL,
    question TEXT,
    answer TEXT,
    sources TEXT
);
"""


def _now():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _clip(text, limit):
    return text[:limit] if text else None


def _connect(db_path=None):
    path = Path(db_path or os.getenv("VAANI_DB") or config.DB_FILE)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def log_unanswered(question, db_path=None):
    question = _clip((question or "").strip(), 500)
    if not question:
        return
    with _lock, closing(_connect(db_path)) as conn, conn:
        conn.execute("INSERT INTO unanswered (created_at, question) VALUES (?, ?)",
                     (_now(), question))


def add_feedback(helpful, status=None, trust=None, score=None, question=None,
                 answer=None, sources=None, db_path=None):
    """Save one thumbs up/down. Text is kept ONLY for thumbs down."""
    if helpful:
        question = answer = sources = None
    else:
        question, answer = _clip(question, 500), _clip(answer, 2000)
        sources = _clip("; ".join(sources or []), 500) or None
    with _lock, closing(_connect(db_path)) as conn, conn:
        cursor = conn.execute(
            "INSERT INTO feedback (created_at, helpful, status, trust, score, question, answer, sources) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (_now(), 1 if helpful else 0, _clip(status, 20), _clip(trust, 20), score,
             question, answer, sources))
        return cursor.lastrowid


def stats(db_path=None):
    """Counts only. Safe to show publicly."""
    with _lock, closing(_connect(db_path)) as conn:
        one = lambda sql: conn.execute(sql).fetchone()[0]
        return {
            "unanswered": one("SELECT COUNT(*) FROM unanswered"),
            "feedback": one("SELECT COUNT(*) FROM feedback"),
            "helpful": one("SELECT COUNT(*) FROM feedback WHERE helpful = 1"),
            "not_helpful": one("SELECT COUNT(*) FROM feedback WHERE helpful = 0"),
        }


def list_unanswered(limit=50, db_path=None):
    with _lock, closing(_connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT created_at, question FROM unanswered ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]


def list_not_helpful(limit=50, db_path=None):
    with _lock, closing(_connect(db_path)) as conn:
        rows = conn.execute(
            "SELECT created_at, status, trust, score, question, answer, sources "
            "FROM feedback WHERE helpful = 0 ORDER BY id DESC LIMIT ?", (limit,))
        return [dict(r) for r in rows]
