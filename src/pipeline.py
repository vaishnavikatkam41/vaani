"""The whole brain in one place. Order matters (this is the core design):

 1. Emergency Fast Lane   (runs first, always)
 2. Dose-request check
 3. Add conversation context (for short follow-up questions)
 4. Retrieval             (find passages)
 5. "I don't know" check  (score too low)
 6. Answer                (LLM if key is set, else extractive baseline)
 7. Safety filter         (remove dose / diagnosis sentences)
 8. Trust Meter + sources
"""
import csv
import json
import time
from pathlib import Path

from . import answer, config, llm, safety
from .conversation import SessionStore
from .retrieval import get_retriever


class Vaani:
    def __init__(self, retriever_kind="tfidf", chunks=None, log_unanswered=True):
        if chunks is None:
            if not config.CHUNKS_FILE.exists():
                raise FileNotFoundError(
                    "data/chunks.json not found. Put PDFs in data/sources/ and run: py -m src.ingest")
            chunks = json.loads(config.CHUNKS_FILE.read_text(encoding="utf-8"))
        self.retriever = get_retriever(retriever_kind, chunks)
        self.kind = self.retriever.kind
        self.sessions = SessionStore()
        self.log_unanswered = log_unanswered

    # ----- helpers -----
    def _result(self, status, text_en, text_te=None, **extra):
        result = {"status": status, "answer": text_te or text_en,
                  "answer_en": text_en, "answer_te": text_te,
                  "trust": extra.pop("trust", None), "sources": extra.pop("sources", []),
                  "score": extra.pop("score", None), "language": extra.pop("language", "en")}
        result.update(extra)
        return result

    def _fixed(self, status):
        msg = safety.MESSAGES[status]
        return self._result(status, msg["en"], msg["te"], language="te")

    def _log_unanswered(self, question):
        """Save the question only (no name, no phone, no id) so we know what sources to add."""
        path = Path(config.UNANSWERED_LOG)
        new_file = not path.exists()
        with open(path, "a", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            if new_file:
                writer.writerow(["time", "question"])
            writer.writerow([time.strftime("%Y-%m-%d %H:%M"), question])

    # ----- main -----
    def ask(self, text, session_id=None):
        text = (text or "").strip()
        if not text:
            return self._fixed("idk")

        # 1. Emergency Fast Lane: runs before everything else
        danger = safety.check_emergency(text)
        if danger:
            return self._fixed(danger)

        # 2. We never give doses
        if safety.is_dose_request(text):
            return self._fixed("refuse")

        # 3. Short follow-up ("he is also vomiting") -> join with the last question
        query = text
        if session_id and len(text.split()) < config.SHORT_QUESTION_WORDS:
            previous = self.sessions.previous_question(session_id)
            if previous:
                query = previous + " " + text

        # 4. Retrieval
        hits = self.retriever.search(query, k=config.TOP_K)
        top_score = hits[0]["score"] if hits else 0.0

        # 5. Too weak a match -> "I don't know"
        trust = answer.trust_level(top_score, self.kind)
        if trust == "idk":
            if self.log_unanswered:
                self._log_unanswered(text)
            return self._fixed("idk") | {"score": top_score, "trust": "idk"}

        # 6. Write the answer
        language, body = "en", ""
        if llm.available():
            try:
                body = llm.write_answer(query, hits) or ""
                language = "te" if body else "en"
            except Exception as error:  # network or key problem: fall back to the baseline
                print("LLM error, using baseline:", error)
        if not body:
            body = answer.pick_sentences(query, hits)
            language = "en"

        # 7. Safety filter
        body, _removed = safety.filter_answer(body)
        if not body:
            # Nothing safe left. If sources only had doses, refuse; if nothing matched, say IDK.
            status = "refuse" if _removed else "idk"
            if status == "idk" and self.log_unanswered:
                self._log_unanswered(text)
            return self._fixed(status) | {"score": top_score, "trust": trust}

        # 8. Trust Meter prefix + sources
        body = answer.TRUST_PREFIX[trust][language] + body
        sources = answer.source_list(hits)
        if session_id:
            self.sessions.add_turn(session_id, text, body)
        return self._result("ok", body if language == "en" else "", body if language == "te" else None,
                            trust=trust, sources=sources, score=top_score, language=language)

    def end(self, session_id):
        """User closed the app: forget the conversation."""
        self.sessions.end(session_id)
