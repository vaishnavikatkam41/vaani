"""Settings for Vaani. All paths and numbers live here, so they are easy to change."""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# Where files live
SOURCES_DIR = ROOT / "data" / "sources"          # put your WHO / government PDFs here
SOURCES_CSV = ROOT / "data" / "sources.csv"      # data sheet: file, friendly name, link, date
CHUNKS_FILE = ROOT / "data" / "chunks.json"      # made by src/ingest.py
UNANSWERED_LOG = ROOT / "data" / "unanswered_log.csv"
TEST_QUESTIONS = ROOT / "data" / "test_questions.csv"
EVAL_DIR = ROOT / "eval"

# Chunking: how big each piece of a document is
CHUNK_WORDS = 120
CHUNK_OVERLAP = 30
MIN_CHUNK_WORDS = 20

# Retrieval: how many passages to look at
TOP_K = 3

# Trust thresholds per retriever: (below first = "I don't know",
# below second = "not fully sure", above second = "sure").
# These are STARTING GUESSES. Tune them with eval/run_eval.py.
THRESHOLDS = {
    "tfidf": (0.12, 0.25),
    "embedding": (0.78, 0.85),
}

# Conversation memory (kept only in RAM, never saved to disk)
SESSION_MAX_TURNS = 3
SESSION_TTL_SECONDS = 30 * 60
SHORT_QUESTION_WORDS = 6   # shorter questions are joined with the previous question

# Database (SQLite: one file, built into Python, nothing to install).
# It stores NO conversations, NO voices, NO names. Only: questions Vaani could not answer,
# and thumbs up / thumbs down feedback. Override the path with the VAANI_DB variable.
DB_FILE = ROOT / "data" / "vaani.db"
