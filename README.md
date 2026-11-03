# Vaani
Telugu voice health assistant for people who cannot read or type well.

## Who it is for
Elderly, rural and daily-wage workers who speak Telugu.

## Topic
General health awareness. Starting with a small set of common topics.

## Safety rule
General awareness only. No diagnosis. No medicine doses.
If unsure, Vaani says: "I don't know, please ask a doctor or ASHA worker."
Danger words (chest pain, fits, heavy bleeding, snake bite...) skip everything and say: go to the hospital, call 108.

## How the brain works
1. Emergency Fast Lane (`src/safety.py`)
2. Dose-request check
3. Short memory of the current chat only (`src/conversation.py`)
4. Search verified sources (`src/retrieval.py`)
5. "I don't know" if the match is weak
6. Grounded answer (`src/answer.py`, optional LLM in `src/llm.py`)
7. Safety filter removes doses and diagnosis
8. Trust Meter + source name

## Run it
```
py -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
1. Put source PDFs in `data/sources/` (names listed in `data/sources.csv`)
2. `py -m src.ingest` cuts them into chunks
3. `py -m src.cli` chat in the terminal
4. `py -m eval.run_eval` measure it
5. `py -m uvicorn app.api:app --reload` start the API (test page: http://127.0.0.1:8000/docs)
6. `py -m unittest discover -s tests -t . -v` run the tests

## Results
See `eval/results.md` and `eval/log.csv` after each run.
