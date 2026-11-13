# Vaani - Project Handoff

## What Vaani is
A Telugu voice health assistant for people who cannot read or type well. One big mic button, no login.
Answers only from WHO / Govt of India sources. General awareness only. No diagnosis, no doses.
Unsure = "I don't know, ask a doctor or ASHA worker". Emergency words = "go to hospital, call 108".
Every answer names its sources. Chat memory lasts only for the current conversation.

## Pipeline order
emergency check -> dose check -> follow-up context -> retrieval -> "I don't know" check -> answer -> safety filter -> translate to Telugu -> Trust Meter + sources

## Built and working (34 tests pass)
- RAG brain (src/): ingest, TF-IDF + multilingual-e5 retriever, safety, answer, pipeline, conversation
- Voice: faster-whisper (ASR), gTTS (TTS), deep-translator (EN->TE)
- FastAPI server (app/api.py): /ask /ask_voice /feedback /stats /admin/unanswered /end /audio /health
- PWA front end (app/static/): big teal mic, topic list, trust bar, source chips, thumbs, 108 button, emergency overlay, dark mode
- SQLite database (src/db.py): unanswered questions + feedback. No conversations, voices or names saved.
- Eval (eval/run_eval.py, 24 questions), Docker + Hugging Face deploy kit (deploy/make_space.py)

## Honest limits
- 24 test questions is small. Need 140+.
- Machine translation is a stop-gap. Whisper small is weak in Telugu.
- Embedding thresholds (0.78, 0.85) are still guesses.
- No ASHA review, no real-voice WER test yet.
- HF Space disk resets on restart, so the database resets too.

## Run locally
    venv\Scripts\activate
    py -m unittest discover -s tests -t .
    py -m uvicorn app.api:app
Open http://127.0.0.1:8000 in Chrome. First voice use downloads a ~480 MB model.

## Deploy
    py deploy\make_space.py
Upload the ../vaani-space folder through the Hugging Face browser (Docker Space).
Optional secret: VAANI_ADMIN_TOKEN (turns on /admin/unanswered).

## Attach to a new chat
1. Project zip (code only, no venv, no PDFs)
2. data/chunks.json and data/cache/embeddings_*.npy
3. eval/results.md and eval/log.csv
4. Your original brief file
5. This HANDOFF.md

## Next later
140+ question test set, LLM Telugu answers, real voice data + WER, dialect/noise report, ASHA review of emergency words, case study, demo video, interview Q&A.
