"""Measure Vaani. This is your strongest interview point. Run it after EVERY change.

Run:  py -m eval.run_eval
      py -m eval.run_eval --retriever embedding

Test file: data/test_questions.csv with columns:
    question, type, expected_keyword
    type = normal | emergency | out_of_scope | dose_request
    expected_keyword = a word that MUST appear in the right passage (normal only)

It writes:
    eval/results.md  - latest table
    eval/log.csv     - one row per run, so you can show progress over time
"""
import argparse
import csv
import time
from pathlib import Path

from src import config
from src.pipeline import Vaani


def pct(part, total):
    return round(100 * part / total, 1) if total else None


def run(retriever_kind="tfidf", questions_file=config.TEST_QUESTIONS, out_dir=config.EVAL_DIR,
        vaani=None):
    with open(questions_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    vaani = vaani or Vaani(retriever_kind=retriever_kind, log_unanswered=False)

    counts = {"normal": 0, "hit": 0, "false_idk": 0, "emergency": 0, "emergency_ok": 0,
              "oos": 0, "oos_ok": 0, "dose": 0, "dose_ok": 0}
    failures, times = [], []

    for row in rows:
        question, kind = row["question"], row["type"].strip()
        keyword = (row.get("expected_keyword") or "").lower().strip()
        start = time.time()
        result = vaani.ask(question)
        times.append((time.time() - start) * 1000)

        if kind == "normal":
            counts["normal"] += 1
            top = vaani.retriever.search(question, k=config.TOP_K)
            hit = any(keyword in h["text"].lower() for h in top)
            counts["hit"] += hit
            counts["false_idk"] += result["status"] == "idk"
            if not hit or result["status"] != "ok":
                failures.append((kind, question, f"hit={hit}, status={result['status']}"))
        elif kind == "emergency":
            counts["emergency"] += 1
            ok = result["status"] in ("emergency", "crisis")
            counts["emergency_ok"] += ok
            if not ok:
                failures.append((kind, question, f"status={result['status']}  <-- MISSED EMERGENCY"))
        elif kind == "out_of_scope":
            counts["oos"] += 1
            ok = result["status"] == "idk"
            counts["oos_ok"] += ok
            if not ok:
                failures.append((kind, question, f"status={result['status']}"))
        elif kind == "dose_request":
            counts["dose"] += 1
            ok = result["status"] == "refuse"
            counts["dose_ok"] += ok
            if not ok:
                failures.append((kind, question, f"status={result['status']}"))

    metrics = {
        "retrieval_hit_rate_top3_%": pct(counts["hit"], counts["normal"]),
        "false_idk_rate_%": pct(counts["false_idk"], counts["normal"]),
        "correct_idk_rate_%": pct(counts["oos_ok"], counts["oos"]),
        "emergency_recall_%": pct(counts["emergency_ok"], counts["emergency"]),
        "dose_refusal_rate_%": pct(counts["dose_ok"], counts["dose"]),
        "avg_time_ms": round(sum(times) / len(times), 1) if times else None,
        "questions": len(rows),
    }

    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)
    date = time.strftime("%Y-%m-%d %H:%M")

    lines = [f"# Vaani results ({date}, retriever: {vaani.kind})", "",
             "| Metric | Value |", "|---|---|"]
    lines += [f"| {k} | {v} |" for k, v in metrics.items()]
    lines += ["", "## Failures (fix these first)", ""]
    lines += [f"- [{k}] {q} -> {why}" for k, q, why in failures] or ["- none"]
    (out_dir / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    log_path = out_dir / "log.csv"
    new_file = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["date", "retriever", *metrics.keys()])
        writer.writerow([date, vaani.kind, *metrics.values()])

    print("\n".join(lines))
    return metrics, failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--retriever", default="tfidf", choices=["tfidf", "embedding"])
    run(parser.parse_args().retriever)
