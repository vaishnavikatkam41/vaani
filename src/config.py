"""Settings for Vaani. All paths and numbers live here, so they are easy to change."""
import os
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
# Which search the app and eval use. Override with the VAANI_RETRIEVER variable.
DEFAULT_RETRIEVER = os.getenv("VAANI_RETRIEVER", "rerank")

# Trust thresholds per retriever: (below first = "I don't know",
# below second = "not fully sure", above second = "sure").
# These are STARTING GUESSES. Tune them with eval/run_eval.py.
THRESHOLDS = {
    "tfidf": (0.12, 0.25),
    "embedding": (0.79, 0.82),   # dev-tuned 0.789; only 84.2% right on the test split - off-topic leaks through
    # Reranker scores are 0..1 probabilities. Cut-off 0.091 chosen on the dev split by
    # tools/tune_thresholds.py -> 98.2% right on the unseen test split (2026-11-13).
    # 0.5 = the reranker thinks it is more likely than not that the passage answers.
    "rerank": (0.091, 0.5),
}

# Conversation memory (kept only in RAM, never saved to disk)
SESSION_MAX_TURNS = 3
SESSION_TTL_SECONDS = 30 * 60
SHORT_QUESTION_WORDS = 6   # shorter questions are joined with the previous question

# Database (SQLite: one file, built into Python, nothing to install).
# It stores NO conversations, NO voices, NO names. Only: questions Vaani could not answer,
# and thumbs up / thumbs down feedback. Override the path with the VAANI_DB variable.
DB_FILE = ROOT / "data" / "vaani.db"
