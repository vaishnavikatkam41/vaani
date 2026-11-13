# Vaani (వాణి)

**A Telugu voice health-awareness assistant for people who cannot read or type.**
Tap one big button, ask a health question in Telugu, and hear a short answer that names its source.

> Vaani gives **general health awareness only**. It never diagnoses and never gives medicine doses.
> When it is not sure, it says: *"I don't know, please ask a doctor or ASHA worker."*

![status](https://img.shields.io/badge/status-V1%20working-teal) ![python](https://img.shields.io/badge/python-3.11+-blue) ![tests](https://github.com/vaishnavikatkam41/vaani/actions/workflows/ci.yml/badge.svg)

---

## 1. Why this project exists

Many people in rural Andhra Pradesh and Telangana (elderly people, daily-wage workers, women at home) cannot read or type.
Health apps need text. Phones can listen. Vaani is built for them:

- **No login, no typing, no reading.** One big round microphone.
- **Telugu in, Telugu out.** Speech to text, search, answer, text to speech.
- **Trust first.** Every answer shows its source and a trust meter. Weak match means "I don't know".
- **Emergency first.** Danger words skip everything and say: go to the hospital, call 108.

## 2. What it does today (V1)

| Area | Status |
|---|---|
| One big mic, picture-icon topic tiles (fever, pregnancy, baby, injury) | Done |
| Telugu speech to text (Sarvam AI, Whisper as backup) | Done |
| Grounded answers from 12 official WHO / Govt of India guides (RAG) | Done |
| Telugu question → English search (NLLB + health glossary) + reranker | Done |
| 150-question evaluation (English + Telugu), dev/test split, public metrics page | Done |
| "I don't know" when sources do not answer | Done |
| Emergency fast lane + one-tap 108 / ASHA / PHC calls | Done |
| Listen again / slower playback | Done |
| Thumbs up/down feedback, unanswered-question log (SQLite) | Done |
| Night mode, installable web app (PWA), low-vision friendly sizes | Done |
| 55 automated tests + GitHub CI | Done |

See the [Roadmap](#11-roadmap) for what is planned.

## 3. How it works

```mermaid
flowchart TD
    A[Villager speaks Telugu] --> B[Speech to text<br/>Sarvam AI, Whisper fallback]
    B --> C{Emergency words?}
    C -- yes --> D[Go to hospital, call 108]
    C -- no --> E{Asks for a dose?}
    E -- yes --> F[Refuse, ask a doctor]
    E -- no --> G[Join with short chat memory]
    G --> T[Telugu → English search text<br/>NLLB + health glossary]
    T --> H[Search verified sources<br/>embeddings + FAISS, top 10]
    H --> R[Reranker reads question + passage<br/>bge-reranker-v2-m3]
    R --> I{Reranker score ≥ 0.086?}
    I -- no --> J["I don't know, ask a doctor or ASHA"]
    I -- yes --> K[Write grounded answer<br/>LLM from passages only]
    K --> L{LLM says NO_ANSWER?}
    L -- yes --> J
    L -- no --> M[Safety filter<br/>remove doses and diagnosis]
    M --> N[Telugu text + trust meter + source names]
    N --> O[Text to speech]
```

The code for each step:

| Step | File |
|---|---|
| Emergency / crisis fast lane, dose check | `src/safety.py` |
| Short memory of the current chat only | `src/conversation.py` |
| Telugu question → English search text | `src/query_translate.py`, `data/glossary_te_en.csv` |
| Search (embeddings + FAISS, then reranker; TF-IDF fallback) | `src/retrieval.py` |
| Answer writing (extractive, or LLM) | `src/answer.py`, `src/llm.py` |
| Whole pipeline and trust meter | `src/pipeline.py` |
| Telugu speech to text | `src/asr.py` |
| Text to speech, English to Telugu translation | `src/tts.py`, `src/translate.py` |
| Database (unanswered questions, feedback) | `src/db.py` |
| Web API | `app/api.py` |
| Web app (PWA) | `app/static/` |

## 4. Safety rules (never broken)

1. General awareness only. **No diagnosis.**
2. **No medicine doses.** Dose requests are refused and sent to a doctor.
3. If the sources do not clearly answer, say **"I don't know"**.
4. Emergency words (chest pain, fits, heavy bleeding, snake bite and more) skip the normal flow: *go to hospital, call 108*.
5. Every answer **names its source**.
6. No photo-based diagnosis.
7. Chat memory lives only for the current chat.
8. **Privacy:** no login, no names, no voice recordings saved. Only unanswered questions and thumbs-down feedback are stored.

These rules are enforced in code and covered by tests (`tests/test_safety.py`, `tests/test_pipeline.py`).

## 5. Tech stack

- **Deep Learning:** multilingual-e5-small embeddings (Telugu question to English passage), Whisper (faster-whisper) ASR fallback, Sarvam AI speech and language models.
- **Data Science:** PDF cleaning and chunking, vector search with FAISS, threshold tuning with probe questions, evaluation set with hit-rate metrics, k-means topic clustering (planned for the ASHA dashboard).
- **Backend:** Python, FastAPI, SQLite.
- **Frontend:** plain HTML, CSS and JavaScript (installable PWA). No framework. Hind Guntur font, "Pasupu" turmeric design.
- **Voice:** Sarvam speech-to-text (`te-IN`), gTTS for speech out.

## 6. Run it on your laptop

> **Setting up on a new computer?** Follow [READIO.md](READIO.md): a complete step-by-step setup with a check after every step.

You need Python 3.11+ and a free Sarvam AI key from https://dashboard.sarvam.ai.

**macOS / Linux**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt -r requirements-voice.txt
export SARVAM_API_KEY="your_key_here"
python -m uvicorn app.api:app --port 8001
```

**Windows (PowerShell)**
```powershell
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt -r requirements-voice.txt
$env:SARVAM_API_KEY="your_key_here"
py -m uvicorn app.api:app --port 8001
```

The first start downloads the models (~5 GB: embeddings, reranker, NLLB, Whisper) and takes about 35 s to load them.

Open http://127.0.0.1:8001 in Chrome and allow the microphone.

**Without a key** Vaani still works, but with weaker Telugu: Whisper for speech and extractive answers.
**Never put your key in a file or on GitHub.** Use the environment variable only.

### Build the knowledge base

```bash
python -m src.fetch_sources   # downloads the 12 official PDFs listed in data/sources.csv (~33 MB)
python -m src.ingest          # cuts them into ~1,900 passages
python -m src.cli             # try it in the terminal
```

PDFs are not stored in this repository. Their official links are in `data/sources.csv`, and
`data/sources/manifest.json` records the size and SHA-256 of each file Vaani was tested with.

## 7. Results (150 questions, 2026-11-13)

| Measure | All | English | Telugu |
|---|---|---|---|
| Emergencies caught | **100%** | 100% | 100% |
| Dose questions refused | **100%** | 100% | 100% |
| Right passage in top 3 | **95.7%** | 96.7% | 93.8% |
| Off-topic correctly refused ("I don't know") | **95.8%** | 93.3% | 100% |

**What changed the numbers.** With embeddings alone, off-topic questions ("How do I learn English?", 0.84)
scored *higher* than real Telugu health questions (0.80), so no cut-off could separate them.
Two fixes: (1) translate the Telugu question to English with NLLB plus a health glossary
(Telugu hit rate 59% → 91%); (2) a cross-encoder reranker scores question + passage together,
pushing off-topic scores to about 0.00. The "I don't know" cut-off was tuned on the dev half
of the questions and measured on the unseen test half:

| Search | Right decision on unseen questions | Off-topic wrongly answered |
|---|---|---|
| Embeddings only | 84.2% | 8 of 11 |
| Translate + rerank | **98.2%** | **0 of 11** |

Live page: `/metrics.html`. Full table: `eval/results.md`. Label corrections are logged in `eval/LABEL_CHANGES.md`.

## 8. Test and measure

```powershell
python -m unittest discover -s tests -t . -v      # 55 tests (also run by GitHub CI on every push)
python -m eval.run_eval                           # 150 questions -> eval/results.md + results.json
python -m tools.tune_thresholds --retriever rerank  # pick the "I don't know" cut-off on dev, report on test
```

Results are written to `eval/results.md` and `eval/log.csv` after each run.

**Known limits (honest list):**
- The 150 questions were written by the team, not collected from villagers. Telugu questions need native-speaker review.
- Evaluation runs with the answer LLM off, so it measures search and safety, not the final Telugu wording.
- Sources do not yet cover first aid for burns/cuts, typhoid, or exercise for elderly people well.
- Search takes ~0.8 s on a laptop (translation + reranker), and the models need ~6 GB of RAM.

## 9. API

| Route | What it does |
|---|---|
| `POST /ask` | Text question, returns answer, trust, sources |
| `POST /ask_voice` | Audio upload, returns transcript and answer |
| `POST /feedback` | Thumbs up/down on an answer |
| `GET /stats` | Counts only (no personal data) |
| `GET /metrics/data` | Latest evaluation numbers (for `/metrics.html`) |
| `GET /admin/unanswered` | Unanswered questions. Needs header `X-Admin-Token` (set `VAANI_ADMIN_TOKEN`) |
| `GET /audio/{name}` | Spoken answer |
| `POST /end` | Clear the chat memory |
| `GET /health` | Server check |

Interactive docs: http://127.0.0.1:8001/docs

## 10. Project layout

```
app/            FastAPI server and the web app (app/static)
src/            The brain: safety, retrieval, answer, LLM, ASR, TTS, DB
data/           sources.csv (links to PDFs), test_questions.csv
eval/           Evaluation runner and results
tests/          45 automated tests
tools/          Small helper scripts (probe.py)
deploy/         Hugging Face Spaces files
Dockerfile      Container build
HANDOFF.md      Notes for the next work session
```

## 11. Roadmap

**Next (backend):** daily source watcher (WHO, MoHFW, NCDC), raw PDF archive with date and hash, cleaning and deduplication, topic labels with multilingual embeddings, DuckDB store, coverage dashboard.
**Star features:** "tell the doctor" summary, myth buster, speaker ID so one phone serves a whole family.
**ASHA dashboard:** weekly questions by topic, emergency count, clustering of questions, unanswered log.
**Quality:** nightly evaluation (hit rate, grounded rate, emergency recall, word error rate) sent to Telegram; 140+ question test set.
**Later:** medicine reminders (no dose advice), medicine strip reader, vaccine and pregnancy calendar, report reader (no interpretation), shake-to-call-108 with location to family, private mode, govt scheme guide (Aarogyasri, Ayushman Bharat), low-data mode, IVR / missed-call access.
**Deploy:** Hugging Face Spaces (`deploy/make_space.py`).

## 12. Sources and disclaimer

Answers come from public WHO and Government of India health guides listed in `data/sources.csv`.
Vaani is an awareness tool. It is **not** a doctor and does not replace one. In an emergency, call **108**.

## 13. Author

Sai Vaishnavi Katkam, B.Tech, KL University. Built as a placement and self-learning project (Deep Learning + Data Science).
GitHub: https://github.com/vaishnavikatkam41
