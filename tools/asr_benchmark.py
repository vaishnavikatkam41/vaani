"""Compare Telugu speech-to-text engines. Lower error = better.

Run:
    python -m tools.asr_benchmark --fleurs-dir <folder> --health-dir <folder> \
        --engines whisper-small-hint whisper-small hf:vasista22/whisper-telugu-small sarvam

Test audio (not stored in Git):
  * FLEURS Telugu test set: real people reading Telugu sentences (Google, CC-BY 4.0).
    https://huggingface.co/datasets/google/fleurs  (data/te_in/test.tsv + audio/test.tar.gz)
  * Health questions: Telugu questions from data/test_questions.csv, read aloud by a
    speech engine (gTTS). Clean synthetic voice: an EASY case, not real villagers.

Metrics (standard for speech recognition):
  CER = character error rate, WER = word error rate (edits / reference length).
  Telugu words are long, so CER is the fairer number. 0% is perfect.

Engines:
  whisper-small-hint   faster-whisper small + Telugu hint sentence (the OLD default)
  whisper-small        faster-whisper small, no hint
  hf:<model id>        any Hugging Face Whisper model, e.g. a Telugu fine-tune
  sarvam               Sarvam AI cloud (needs SARVAM_API_KEY)
"""
import argparse
import csv
import json
import os
import re
import time
from pathlib import Path

from src import config

PUNCT = re.compile(r"[^\w\sఀ-౿]")


def normalise(text):
    return re.sub(r"\s+", " ", PUNCT.sub(" ", (text or "").lower())).strip()


def edits(a, b):
    """Levenshtein distance between two sequences."""
    prev = list(range(len(b) + 1))
    for i, x in enumerate(a, 1):
        cur = [i]
        for j, y in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (x != y)))
        prev = cur
    return prev[-1]


def load_fleurs(folder, limit):
    folder = Path(folder)
    tsv = folder / "test.tsv"
    wavs = {p.name: p for p in folder.rglob("*.wav")}
    items = []
    with open(tsv, encoding="utf-8") as f:
        for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
            if len(row) > 2 and row[1] in wavs:
                items.append({"file": str(wavs[row[1]]), "text": row[2], "set": "fleurs"})
            if len(items) >= limit:
                break
    return items


def load_health(folder, limit):
    items = json.loads((Path(folder) / "items.json").read_text(encoding="utf-8"))
    return [dict(i, set="health") for i in items[:limit]]


def make_engine(name):
    from src import asr
    if name == "sarvam":
        key = os.environ["SARVAM_API_KEY"]
        return lambda path: asr._sarvam(path, key)
    if name in ("whisper-small-hint", "whisper-small"):
        from faster_whisper import WhisperModel
        model = WhisperModel("small", device="cpu", compute_type="int8")
        hint = asr.OLD_HINT if name.endswith("hint") else None

        def run(path):
            segs, _ = model.transcribe(path, language="te", vad_filter=True, beam_size=5,
                                       initial_prompt=hint, condition_on_previous_text=False)
            return " ".join(s.text.strip() for s in segs)
        return run
    if name.startswith("hf:"):
        return asr.HFWhisper(name[3:]).transcribe
    raise ValueError(name)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--fleurs-dir")
    p.add_argument("--health-dir")
    p.add_argument("--limit", type=int, default=25)
    p.add_argument("--engines", nargs="+", required=True)
    args = p.parse_args()

    items = []
    if args.fleurs_dir:
        items += load_fleurs(args.fleurs_dir, args.limit)
    if args.health_dir:
        items += load_health(args.health_dir, args.limit * 3)
    print(f"{len(items)} clips")

    results = {}
    for name in args.engines:
        engine = make_engine(name)
        engine(items[0]["file"])               # warm-up (model load), not timed
        per_set, t0, examples = {}, time.time(), []
        for it in items:
            hyp = engine(it["file"])
            ref_n, hyp_n = normalise(it["text"]), normalise(hyp)
            s = per_set.setdefault(it["set"], [0, 0, 0, 0])
            s[0] += edits(ref_n, hyp_n); s[1] += len(ref_n)
            s[2] += edits(ref_n.split(), hyp_n.split()); s[3] += len(ref_n.split())
            if it["set"] == "health" and len(examples) < 4:
                examples.append((it["text"], hyp))
        secs = (time.time() - t0) / len(items)
        results[name] = {k: {"cer_%": round(100 * v[0] / v[1], 1), "wer_%": round(100 * v[2] / v[3], 1)}
                         for k, v in per_set.items()} | {"sec_per_clip": round(secs, 2)}
        print(f"\n{name}: {results[name]}")
        for ref, hyp in examples:
            print(f"   said: {ref}\n   got : {hyp}")

    out = config.EVAL_DIR / "asr_results.json"
    saved = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    saved.update({k: dict(v, date=time.strftime("%Y-%m-%d")) for k, v in results.items()})
    out.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nSaved to {out}")


if __name__ == "__main__":
    main()
