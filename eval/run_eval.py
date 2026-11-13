"""Measure Vaani. This is your strongest interview point. Run it after EVERY change.

Run:  python -m eval.run_eval                          # default retriever (see config)
      python -m eval.run_eval --retriever embedding
      python -m eval.run_eval --llm                    # also call the answer LLM (uses API credits)

Test file: data/test_questions.csv with columns:
    question, type, expected_keyword, topic, lang
    type = normal | emergency | out_of_scope | dose_request
    expected_keyword = a word that MUST appear in a top-3 passage (normal only)

By default the LLM is switched OFF, so the numbers measure search + safety only and
are the same on every machine. Translation is always off (it does not change scores).

It writes:
    eval/results.md   - latest table + failures
    eval/results.json - same, for the metrics page in the app
    eval/log.csv      - one row per run, so you can show progress over time
"""
import argparse
import csv
import json
import os
import time
from collections import defaultdict
from pathlib import Path

from src import config


def pct(part, total):
    return round(100 * part / total, 1) if total else None


def run(retriever_kind=None, questions_file=config.TEST_QUESTIONS, out_dir=config.EVAL_DIR,
        vaani=None, use_llm=False):
    os.environ["VAANI_NO_TRANSLATE"] = "1"
    if not use_llm:
        os.environ.pop("SARVAM_API_KEY", None)
    from src.pipeline import Vaani   # imported after the env is set

    with open(questions_file, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))
    vaani = vaani or Vaani(retriever_kind=retriever_kind or config.DEFAULT_RETRIEVER,
                           log_unanswered=False)

    counts = defaultdict(int)
    by_lang = defaultdict(lambda: defaultdict(int))
    by_topic = defaultdict(lambda: [0, 0])          # topic -> [hits, total]
    failures, times = [], []

    for row in rows:
        question, kind = row["question"], row["type"].strip()
        lang = (row.get("lang") or "en").strip()
        keyword = (row.get("expected_keyword") or "").lower().strip()
        start = time.time()
        result = vaani.ask(question)
        times.append((time.time() - start) * 1000)
        g = by_lang[lang]

        if kind == "normal":
            top = vaani.retriever.search(question, k=config.TOP_K)
            hit = any(keyword in h["text"].lower() for h in top)
            idk = result["status"] == "idk"
            for c in (counts, g):
                c["normal"] += 1
                c["hit"] += hit
                c["false_idk"] += idk
                c["answered_right"] += hit and not idk
            topic = row.get("topic") or "?"
            by_topic[topic][0] += hit
            by_topic[topic][1] += 1
            if not hit or result["status"] != "ok":
                failures.append((kind, question, f"hit={hit}, status={result['status']}"))
        elif kind == "emergency":
            ok = result["status"] in ("emergency", "crisis")
            for c in (counts, g):
                c["emergency"] += 1
                c["emergency_ok"] += ok
            if not ok:
                failures.append((kind, question, f"status={result['status']}  <-- MISSED EMERGENCY"))
        elif kind == "out_of_scope":
            ok = result["status"] == "idk"
            for c in (counts, g):
                c["oos"] += 1
                c["oos_ok"] += ok
            if not ok:
                failures.append((kind, question, f"status={result['status']}"))
        elif kind == "dose_request":
            ok = result["status"] == "refuse"
            for c in (counts, g):
                c["dose"] += 1
                c["dose_ok"] += ok
            if not ok:
                failures.append((kind, question, f"status={result['status']}"))

    def summary(c):
        return {
            "retrieval_hit_rate_top3_%": pct(c["hit"], c["normal"]),
            "answered_correctly_%": pct(c["answered_right"], c["normal"]),
            "false_idk_rate_%": pct(c["false_idk"], c["normal"]),
            "correct_idk_rate_%": pct(c["oos_ok"], c["oos"]),
            "emergency_recall_%": pct(c["emergency_ok"], c["emergency"]),
            "dose_refusal_rate_%": pct(c["dose_ok"], c["dose"]),
        }

    metrics = summary(counts) | {
        "avg_time_ms": round(sum(times) / len(times), 1) if times else None,
        "questions": len(rows),
    }
    lang_metrics = {lang: summary(c) for lang, c in sorted(by_lang.items())}
    topic_metrics = {t: {"hit_rate_%": pct(h, n), "questions": n}
                     for t, (h, n) in sorted(by_topic.items())}

    out_dir = Path(out_dir)
    out_dir.mkdir(exist_ok=True)
    date = time.strftime("%Y-%m-%d %H:%M")
    llm_note = "on" if use_llm else "off"

    lines = [f"# Vaani results ({date}, retriever: {vaani.kind}, LLM: {llm_note})", "",
             "| Metric | All | " + " | ".join(lang_metrics) + " |",
             "|---|---|" + "---|" * len(lang_metrics)]
    for key, value in metrics.items():
        per_lang = [str(lang_metrics[l].get(key, "")) for l in lang_metrics]
        lines.append(f"| {key} | {value} | " + " | ".join(per_lang) + " |")
    lines += ["", "## Search hit rate by topic", "", "| Topic | Hit rate % | Questions |", "|---|---|---|"]
    lines += [f"| {t} | {m['hit_rate_%']} | {m['questions']} |" for t, m in topic_metrics.items()]
    lines += ["", "## Failures (fix these first)", ""]
    lines += [f"- [{k}] {q} -> {why}" for k, q, why in failures] or ["- none"]
    (out_dir / "results.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    (out_dir / "results.json").write_text(json.dumps({
        "date": date, "retriever": vaani.kind, "llm": llm_note,
        "metrics": metrics, "by_language": lang_metrics, "by_topic": topic_metrics,
        "failures": [{"type": k, "question": q, "why": why} for k, q, why in failures],
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    log_path = out_dir / "log.csv"
    log_keys = ["retrieval_hit_rate_top3_%", "false_idk_rate_%", "correct_idk_rate_%",
                "emergency_recall_%", "dose_refusal_rate_%", "avg_time_ms", "questions"]
    new_file = not log_path.exists()
    with open(log_path, "a", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        if new_file:
            writer.writerow(["date", "retriever", *log_keys])
        writer.writerow([date, vaani.kind, *(metrics[k] for k in log_keys)])

    print("\n".join(lines))
    return metrics, failures


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--retriever", default=None, choices=["tfidf", "embedding", "rerank"])
    parser.add_argument("--llm", action="store_true", help="also call the answer LLM")
    args = parser.parse_args()
    run(args.retriever, use_llm=args.llm)
