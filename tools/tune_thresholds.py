"""Pick the "I don't know" cut-off honestly.

Run:  python -m tools.tune_thresholds --retriever rerank

1. Score every normal (should answer) and out_of_scope (should say IDK) question.
2. Choose the cut-off using ONLY the questions marked split=dev.
   Among cut-offs with the best dev accuracy, take the middle of the widest gap
   (largest safety margin).
3. Report accuracy on split=test questions, which the cut-off never saw.

Paste the printed value into config.THRESHOLDS. Changes nothing by itself.
"""
import argparse
import csv
import json
import os
import time

from src import config


def score_rows(kind):
    os.environ["VAANI_NO_TRANSLATE"] = "1"
    from src.pipeline import Vaani
    vaani = Vaani(retriever_kind=kind, log_unanswered=False)
    with open(config.TEST_QUESTIONS, newline="", encoding="utf-8") as f:
        rows = [r for r in csv.DictReader(f) if r["type"] in ("normal", "out_of_scope")]
    out = []
    for r in rows:
        hits = vaani.retriever.search(r["question"], k=config.TOP_K)
        out.append({"score": hits[0]["score"] if hits else 0.0,
                    "should_answer": r["type"] == "normal",
                    "split": r.get("split", "dev"), "lang": r.get("lang", "en"),
                    "question": r["question"]})
    return out


def accuracy(rows, cut):
    ok = sum((r["score"] >= cut) == r["should_answer"] for r in rows)
    return ok, len(rows)


def pick_cut(dev):
    values = sorted({r["score"] for r in dev})
    cuts = [(a + b) / 2 for a, b in zip(values, values[1:])] or values
    best = max(accuracy(dev, c)[0] for c in cuts)
    # among the best cut-offs, prefer the one with the widest gap around it
    gaps = []
    for a, b in zip(values, values[1:]):
        c = (a + b) / 2
        if accuracy(dev, c)[0] == best:
            gaps.append((b - a, c))
    return max(gaps)[1]


def main(kind):
    rows = score_rows(kind)
    dev = [r for r in rows if r["split"] == "dev"]
    test = [r for r in rows if r["split"] == "test"]
    cut = pick_cut(dev)
    print(f"\nretriever: {kind}")
    print(f"chosen 'I don't know' cut-off (from dev only): {cut:.4f}")
    for name, part in (("dev", dev), ("test", test)):
        ok, n = accuracy(part, cut)
        print(f"  {name:4} accuracy: {ok}/{n} = {100 * ok / n:.1f}%")
    for lang in ("en", "te"):
        ok, n = accuracy([r for r in test if r["lang"] == lang], cut)
        if n:
            print(f"  test {lang}: {ok}/{n}")
    print("\nTest-split mistakes:")
    mistakes = []
    for r in test:
        if (r["score"] >= cut) != r["should_answer"]:
            what = "said IDK to a real question" if r["should_answer"] else "answered off-topic"
            mistakes.append(f"{what}: {r['question']}")
            print(f"  {r['score']:.3f}  {what}: {r['question']}")

    # Save for the metrics page (one entry per retriever).
    out = config.EVAL_DIR / "gate_results.json"
    saved = json.loads(out.read_text(encoding="utf-8")) if out.exists() else {}
    test_ok, test_n = accuracy(test, cut)
    off = [r for r in test if not r["should_answer"]]
    saved[kind] = {"cutoff": round(cut, 4), "date": time.strftime("%Y-%m-%d"),
                   "dev_accuracy_%": round(100 * accuracy(dev, cut)[0] / len(dev), 1),
                   "test_accuracy_%": round(100 * test_ok / test_n, 1),
                   "test_offtopic_answered": sum(r["score"] >= cut for r in off),
                   "test_offtopic_total": len(off),
                   "test_mistakes": mistakes}
    out.write_text(json.dumps(saved, ensure_ascii=False, indent=1), encoding="utf-8")
    return cut


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--retriever", default=config.DEFAULT_RETRIEVER,
                   choices=["tfidf", "embedding", "rerank"])
    main(p.parse_args().retriever)
