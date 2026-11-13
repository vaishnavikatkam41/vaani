# READIO: set up Vaani on a new computer

This file is a **step-by-step setup script written in plain English**.
It is meant to be read and followed by an AI coding assistant (or a person) on a fresh machine.
Follow the steps **in order**. After each step, run its **Check** and do not continue until it passes.

Last verified: 2026-11-14 on macOS 27 (Apple Silicon), Python 3.12.13. 62 tests passing, `tools/check_all.py` all green.

---

## Quick start: paste this into your AI coding assistant

Open an AI coding assistant in an empty folder, then paste this whole block:

```text
Set up and run this project on my computer: https://github.com/vaishnavikatkam41/vaani

1. Clone the repository, then open and read READIO.md completely before doing anything else.
2. Before installing anything, ask me every question listed in READIO.md section
   "Questions to ask the user first" (one short message, numbered). Wait for my answers.
3. Then follow READIO.md step by step, in order. After every step run its "Check".
   If a check fails, use the Troubleshooting table, and tell me what happened.
4. Never write my API key into any file except the private .env file described in
   READIO.md, never print it, never commit it.
5. Finish with Step 10 (python -m tools.check_all) and show me the PASS/FAIL list,
   the localhost link, and anything that still needs my action.
```

---

## Questions to ask the user first

An assistant following this file must ask these **before** Step 1 and wait for the answers:

1. Which operating system is this: macOS, Windows or Linux? (Detect it, and just confirm.)
2. Do you have a **Sarvam AI key**? (Free at https://dashboard.sarvam.ai. Without it, Telugu speech
   recognition and Telugu answers are weaker.) If yes: will you paste it into the `.env` file yourself,
   or do you want me to create `.env` and you paste the key into it?
3. Where should the project folder go? (Default: the current folder.)
4. Which branch? (Default: `main`.)
5. Is there at least **12 GB free disk** and **8 GB RAM**? If not, use the light mode (`VAANI_RETRIEVER=tfidf`).
6. Should I also run the full quality evaluation (Step 8, about 5 minutes)? (Default: yes.)
7. Which port for the app? (Default: `8001`.)
8. Are you going to change the code (then I explain the working rules in Section 13), or only run it?

---

## 0. Rules for whoever follows this file

1. Do the steps in order. Each step has a **Check**. If a check fails, use [Troubleshooting](#12-troubleshooting) before moving on.
2. **API keys go only in the private `.env` file** (or the terminal environment). Never in any other file, never committed (`.env` is in `.gitignore`), never printed in full.
3. **Never weaken the safety rules** in `src/safety.py` (emergency words, dose refusal, answer filter). Only add to them.
4. Run commands from the project folder (`vaani/`) unless a step says otherwise.
5. Use the virtual environment's Python (`.venv`) for every Python command after Step 3.
6. If you are unsure what the user wants (for example which Sarvam key to use), **ask the user** instead of guessing.

---

## 1. What you need first

| Need | Minimum | Why |
|---|---|---|
| Git | any recent version | to download the code |
| Python | **3.11 or 3.12** (3.12 recommended) | 3.9/3.10 are too old; 3.13 is untested |
| Free disk space | **12 GB** | ~6 GB of AI models + ~3 GB of Python packages + PDFs |
| RAM | 8 GB (16 GB recommended) | the models use ~6 GB together |
| Internet | yes, for setup | models, packages and PDFs are downloaded once |
| Browser | Chrome or Edge | the microphone works best there |
| Sarvam AI key | optional but recommended | best Telugu speech + Telugu answers. Free at https://dashboard.sarvam.ai |

### Install Git and Python

**macOS** (with Homebrew):
```bash
brew install git python@3.12
```

**Ubuntu / Debian Linux**:
```bash
sudo apt update && sudo apt install -y git python3.12 python3.12-venv libgomp1
```

**Windows** (PowerShell):
```powershell
winget install --id Git.Git -e
winget install --id Python.Python.3.12 -e
```

**Check:**
```bash
git --version
python3.12 --version        # Windows: py -3.12 --version
```
Expected: a git version, and `Python 3.12.x` (or 3.11.x).

---

## 2. Download the code

```bash
git clone https://github.com/vaishnavikatkam41/vaani.git
cd vaani
```

To work on the latest feature branch instead of `main`, list branches and switch:
```bash
git branch -a
git checkout <branch-name>
```

**Check:** `ls` shows `README.md`, `READIO.md`, `src/`, `app/`, `data/`, `tests/`.

---

## 3. Create the Python environment and install packages

**macOS / Linux:**
```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
```

**Windows (PowerShell):**
```powershell
py -3.12 -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
```
(If PowerShell blocks the script: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, then try again.)

### Install the exact tested versions (preferred)

**macOS:**
```bash
pip install -r requirements-lock.txt
```

**Linux / Windows** (CPU-only PyTorch, much smaller download):
```bash
pip install -r requirements-lock.txt --extra-index-url https://download.pytorch.org/whl/cpu
```

### Fallback (only if the lock file fails to install)

```bash
pip install -r requirements.txt -r requirements-voice.txt
```

**Check:**
```bash
python -c "import fastapi, sklearn, pypdf, faiss, sentence_transformers, transformers, sentencepiece, faster_whisper, gtts, deep_translator; print('packages OK')"
```
Expected: `packages OK`.

---

## 4. Set the keys (private `.env` file)

Create the private settings file from the template:

```bash
cp .env.example .env          # Windows: copy .env.example .env
```

Then the **user** opens `.env` in a text editor and pastes their key after `SARVAM_API_KEY=`:
```
SARVAM_API_KEY=their-key-here
```
The server reads `.env` automatically on start. `.env` is in `.gitignore`, so it never reaches GitHub.
(A key set in the terminal with `export SARVAM_API_KEY=...` also works and wins over the file.)

Optional in `.env`: `VAANI_ADMIN_TOKEN=<long random text>` turns on `/admin/unanswered`.

Without a Sarvam key, Vaani still works, with weaker Telugu: a local Telugu speech model, and English
sentences taken straight from the guides (translated to Telugu).

**Check** (prints yes/no, never the key):
```bash
python -c "import os; from src import config; print('Sarvam key found' if os.getenv('SARVAM_API_KEY') else 'no key: basic mode')"
```

---

## 5. Build the knowledge base (official health guides)

The PDFs are not stored in Git. This downloads the 12 official WHO / Government of India guides listed in `data/sources.csv` (about 33 MB):

```bash
python -m src.fetch_sources
```
Expected last lines: `12 files ready, 0 failed`.

Then cut them into searchable passages:
```bash
python -m src.ingest
```
Expected last line: `Total: 1855 chunks from 12 files -> .../data/chunks.json` (the number can differ slightly if a website updated a PDF).

**Check:** compare the downloaded files with the tested versions:
```bash
python -c "
import json,hashlib,pathlib
m=json.load(open('data/sources/manifest.json'))
for f,v in m.items():
    p=pathlib.Path('data/sources')/f
    ok=p.exists() and hashlib.sha256(p.read_bytes()).hexdigest()==v['sha256']
    print('same' if ok else 'DIFFERENT/MISSING', f)
"
```
`DIFFERENT` is not fatal (the government site may have updated the file), but tell the user, and re-run the evaluation in Step 8.

---

## 6. Download the AI models (one time, ~6 GB)

They download automatically on first use, but doing it now makes the first start fast and shows errors early:

```bash
python -c "
from sentence_transformers import SentenceTransformer, CrossEncoder
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from src.asr import HFWhisper, DEFAULT_LOCAL_MODEL
SentenceTransformer('intfloat/multilingual-e5-small'); print('1/4 search model OK')
CrossEncoder('BAAI/bge-reranker-v2-m3'); print('2/4 reranker OK')
n='facebook/nllb-200-distilled-600M'; AutoTokenizer.from_pretrained(n); AutoModelForSeq2SeqLM.from_pretrained(n); print('3/4 translator OK')
HFWhisper(DEFAULT_LOCAL_MODEL); print('4/4 Telugu speech model OK')
"
```

| Model | Size | Job |
|---|---|---|
| `intfloat/multilingual-e5-small` | ~0.5 GB | finds candidate passages (meaning search) |
| `BAAI/bge-reranker-v2-m3` | ~2.2 GB | checks which passage really answers; drives "I don't know" |
| `facebook/nllb-200-distilled-600M` | ~2.5 GB | translates the Telugu question to English for searching |
| Telugu Whisper (see `DEFAULT_LOCAL_MODEL` in `src/asr.py`) | ~1 GB | Telugu speech-to-text when there is no Sarvam key |

Models are saved in `~/.cache/huggingface/` (set `HF_HOME` to move them).

**Check:** all four `OK` lines print.

---

## 7. Run the tests

```bash
python -m unittest discover -s tests -t . -v
```

**Check:** the last lines say `Ran 62 tests` and `OK` (the count grows as tests are added; it must say `OK`).

---

## 8. Run the evaluation (proves search + safety quality)

```bash
python -m eval.run_eval
```
Takes about 3–5 minutes. It writes `eval/results.md` and `eval/results.json`.

**Check:** compare with the tested numbers:

| Measure | Expected |
|---|---|
| emergency_recall_% | **100.0** (must be 100) |
| dose_refusal_rate_% | **100.0** (must be 100) |
| retrieval_hit_rate_top3_% | about 97.8 |
| correct_idk_rate_% | about 95.8 |

If emergency or dose numbers are below 100, **stop and tell the user**. That is a safety problem.

---

## 9. Start the app

```bash
python -m uvicorn app.api:app --port 8001
```
The first start takes ~35 seconds (loading models). Leave this terminal open.

Open in Chrome:
- App: **http://127.0.0.1:8001**
- Quality report: **http://127.0.0.1:8001/metrics.html**
- API docs: **http://127.0.0.1:8001/docs**

Allow the microphone when Chrome asks. (The microphone only works on `localhost`/`127.0.0.1` or `https`.)

**Check** (in a second terminal):
```bash
curl -s http://127.0.0.1:8001/health      # shows which speech / answer / search engines are on
curl -s http://127.0.0.1:8001/ask -H "content-type: application/json" -d '{"text":"What are the symptoms of dengue?"}'
curl -s http://127.0.0.1:8001/ask -H "content-type: application/json" -d '{"text":"My father has chest pain"}'
```
Expected: the dengue question returns `"status":"ok"` with a government dengue guide in `sources`; the chest pain question returns `"status":"emergency"`.

To use another port, change `8001`. To stop the server: `Ctrl + C`.

---

## 10. Final check: test every feature

With the server running, in a second terminal (virtual environment active):

```bash
python -m tools.check_all                 # or: --url http://127.0.0.1:<port>
```

It tests the pages, every picture tile, all safety rules (emergency, suicide crisis, dose
refusal, off-topic), conversation memory, spoken answers, **voice upload with a recorded Telugu
question**, the quality report, stats and admin lock.

**Check:** the last line says `ALL CHECKS PASSED`. The `answer writer` line says whether Sarvam is on.
Show the user the full list and the link **http://127.0.0.1:8001**.

---

## 11. Environment variables (all optional except the key)

| Variable | Default | What it does |
|---|---|---|
| `SARVAM_API_KEY` | (none) | Sarvam speech-to-text + Telugu answer writing |
| `SARVAM_LLM_MODEL` | `sarvam-105b` | which Sarvam model writes answers |
| `VAANI_RETRIEVER` | `rerank` | search type: `rerank` (best), `embedding`, `tfidf` (lightest) |
| `SARVAM_MODEL` | `saaras:v4` | Sarvam speech-to-text model |
| `VAANI_ASR_MODEL` | see `src/asr.py` | local Telugu speech model (any Hugging Face Whisper id) |
| `VAANI_NLLB_MODEL` | `facebook/nllb-200-distilled-600M` | question translator |
| `VAANI_NO_NLLB` | (unset) | set to `1` to skip the translator (uses glossary only) |
| `VAANI_ADMIN_TOKEN` | (unset) | enables `/admin/unanswered` (send as `X-Admin-Token` header) |
| `VAANI_DB` | `data/vaani.db` | where the SQLite database lives |
| `HF_HOME` | `~/.cache/huggingface` | where AI models are stored |

**Low-memory computer (under 8 GB RAM):** `export VAANI_RETRIEVER=tfidf` (English-only quality, no big models).

---

## 12. Troubleshooting

| Problem | Fix |
|---|---|
| `python3.12: command not found` | Install Python 3.12 (Step 1). On Windows use `py -3.12`. |
| `CERTIFICATE_VERIFY_FAILED` while fetching PDFs | Already handled: the script retries with `curl`. Make sure `curl` is installed. |
| A PDF fails with 404 / connection error | Government sites are sometimes down. Run `python -m src.fetch_sources` again later. Never replace a source with an unofficial copy. |
| `Translation failed ... too many requests` | Google's free translator rate-limited you. Wait 10–30 minutes. Answers fall back to English meanwhile. |
| `Address already in use` | Port 8001 is busy: use `--port 8002`, or stop the other server. |
| First question is very slow | Normal: models load on first use (~35 s). Later questions take ~1–2 s. |
| `Killed` / out of memory | Close other apps, or use `VAANI_RETRIEVER=tfidf`. |
| **Voice is heard wrongly** | Open `http://127.0.0.1:8001/health`. If `speech` says `local:...`, the Sarvam key is missing: put it in `.env` and restart the server. Speak close to the phone, in a quiet place; tap "తప్పుగా విన్నాను? మళ్ళీ చెప్పండి" to say it again. |
| Key in `.env` but `/health` still shows `local:` | Restart the server (it reads `.env` only at start). Check there are no spaces around `=` issues and the line starts with `SARVAM_API_KEY=`. |
| Microphone does nothing | Use Chrome, open `http://127.0.0.1:8001` (not the computer's network IP), allow microphone permission. |
| `ModuleNotFoundError` | The virtual environment is not active. Run `source .venv/bin/activate` (Windows: `.venv\Scripts\Activate.ps1`). |
| `data/chunks.json not found` | Run Step 5. |
| Torch download is huge on Linux | Use the `--extra-index-url https://download.pytorch.org/whl/cpu` line from Step 3. |

---

## 13. Working on the code (after setup)

### Project map

```
app/api.py               web server (FastAPI): /ask, /ask_voice, /feedback, /stats, /metrics/data, ...
app/static/              the phone web app (index.html) and the quality page (metrics.html)
src/safety.py            emergency words, dose refusal, answer filter  <- most important file
src/pipeline.py          the full question -> answer flow
src/retrieval.py         search: tfidf / embedding / rerank
src/query_translate.py   Telugu question -> English search text (translator + glossary)
src/llm.py               Sarvam writes the final answer from the passages only
src/fetch_sources.py     downloads the official PDFs
src/ingest.py            PDFs -> passages (data/chunks.json)
data/sources.csv         the official source list (links, publisher, topic)
data/glossary_te_en.csv  Telugu health words -> English (add rows to improve Telugu search)
data/test_questions.csv  150 evaluation questions, with a dev/test split
eval/run_eval.py         measures quality -> eval/results.md, results.json, log.csv
tools/check_all.py       final check of a running server (every feature, PASS/FAIL)
tools/asr_benchmark.py   compares Telugu speech-to-text engines (error rates)
src/asr.py               speech-to-text: Sarvam saaras:v4 -> local Telugu Whisper
.env.example             template for the private .env (keys)
tools/tune_thresholds.py picks the "I don't know" cut-off on dev, reports on test
tests/                   unit tests (run by GitHub on every push)
```

### Rules for every change

1. Create a branch: `git checkout -b feat/<short-name>`.
2. After any change: run the tests (Step 7). They must pass.
3. After any change to search, sources, glossary or safety: run the evaluation (Step 8) and commit the updated `eval/` files.
4. If you change an expected answer in `data/test_questions.csv`, log it in `eval/LABEL_CHANGES.md` with the reason.
5. To change the "I don't know" cut-off, run `python -m tools.tune_thresholds --retriever rerank` and copy its value into `src/config.py`. Never tune on the test split by hand.
6. New emergency phrases go in `src/safety.py` **and** as a question in `data/test_questions.csv` (type `emergency`).
7. Never commit: API keys, `.venv/`, PDFs, `data/chunks.json`, `data/cache/`, `data/vaani.db` (already in `.gitignore`).

### Adding a new health source

1. Find the **official** PDF (WHO, MoHFW, NHM, NCDC, NCVBDC, ICMR, NHSRC). No blogs, no unofficial copies.
2. Add a row to `data/sources.csv`: `file,friendly_name,topic,publisher,url,date_accessed,license_note`.
3. Run `python -m src.fetch_sources`, then `python -m src.ingest`.
4. Add test questions for the new topic, then run the evaluation.

### Deploy (Hugging Face Spaces, free)

```bash
python deploy/make_space.py
```
This builds `../vaani-space`. Upload that folder to a new **Docker** Space. Add `SARVAM_API_KEY` as a Space **secret** (Settings → Variables and secrets), never in the files.
