"""
============================================================================
bench/generation_eval.py — Generation quality metrics (RAGAS)
============================================================================
WHY THIS EXISTS
---------------
Requirement: "Benchmarking — evaluation of retrieval AND generation."

`retrieval_eval.py` measures whether the right documents are surfaced.
This script measures whether the ANSWER is good, using RAGAS metrics:

- faithfulness       : is every claim in the answer grounded in the context?
                       (no hallucination)
- answer_relevancy   : does the answer actually address the question?
- context_precision  : were the retrieved chunks relevant to the question?

USAGE
-----
    cd backend
    # 1) Generate answers for the eval queries first:
    python bench/generation_eval.py --generate --out answers_baseline.json
    # 2) Score them with RAGAS:
    python bench/generation_eval.py --score --in answers_baseline.json --out results_generation_baseline.json

After fine-tuning, regenerate + rescore, then compare.

NOTE
----
RAGAS uses an LLM-as-judge, so it requires `LLM_PROVIDER != none`. Set
`LLM_PROVIDER=openai` (with OPENAI_API_KEY) before running --score.
For --generate you can use any provider (or none — the stub will produce
a usable-but-shallow answer).
"""
from __future__ import annotations
import argparse
import json
import os
import sys
from pathlib import Path

# Bootstrap Django
BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402
django.setup()

from rag.engine import get_engine  # noqa: E402

EVAL_PATH = Path(__file__).parent / "eval.jsonl"


def load_eval():
    rows = []
    with open(EVAL_PATH, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def generate_answers(out_path: str, max_queries: int = 15):
    """
    For each eval query, call engine.answer() and save:
        {question, answer, contexts (list of snippets), language, reference}
    """
    rows = load_eval()[:max_queries]
    engine = get_engine()
    results = []
    for r in rows:
        print(f"[generate] {r['id']} ({r['language']}) — {r['query'][:50]}")
        resp = engine.answer(r["query"], user=None, language=r["language"])
        results.append({
            "id": r["id"],
            "language": r["language"],
            "question": r["query"],
            "answer": resp["answer"],
            "contexts": [s["snippet"] for s in resp.get("sources", [])],
            "reference": r.get("reference_answer", ""),
        })
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(results)} answers to {out_path}")


def score_with_ragas(in_path: str, out_path: str):
    """Run RAGAS over the generated answers."""
    try:
        from ragas import evaluate
        from ragas.metrics import faithfulness, answer_relevancy, context_precision
        from datasets import Dataset
    except ImportError as e:
        print(f"RAGAS is not installed: {e}")
        print("Run: pip install ragas datasets")
        return

    with open(in_path, encoding="utf-8") as f:
        rows = json.load(f)

    # RAGAS expects: question, answer, contexts, reference (ground_truth)
    data = {
        "question": [r["question"] for r in rows],
        "answer": [r["answer"] for r in rows],
        "contexts": [[r["contexts"]] if isinstance(r["contexts"], str) else r["contexts"] for r in rows],
        "ground_truth": [r["reference"] for r in rows],
        "language": [r["language"] for r in rows],
    }
    ds = Dataset.from_dict(data)

    print(f"[score] Running RAGAS over {len(rows)} answers...")
    try:
        result = evaluate(ds, metrics=[faithfulness, answer_relevancy, context_precision])
    except Exception as e:
        print(f"RAGAS evaluate failed: {e}")
        print("Hint: RAGAS needs LLM_PROVIDER != none. Set OPENAI_API_KEY and retry.")
        return

    # result is a dict-like with metric → score
    out = {
        "overall": {k: float(v) for k, v in dict(result).items()},
        "by_language": {},
        "answers": rows,
    }
    # Per-language breakdown
    from collections import defaultdict
    by_lang = defaultdict(list)
    for i, r in enumerate(rows):
        lang = r["language"]
        scores = {k: float(result[k]) for k in dict(result).keys()}
        by_lang[lang].append(scores)
    for lang, items in by_lang.items():
        out["by_language"][lang] = {
            k: round(sum(it[k] for it in items) / len(items), 4)
            for k in items[0].keys()
        }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 50)
    print("GENERATION BENCHMARK (RAGAS)")
    print("=" * 50)
    print(f"{'Language':<10}{'N':>4}{'faithfulness':>16}{'relevancy':>12}{'ctx_prec':>12}")
    print("-" * 50)
    for lang in sorted(out["by_language"].keys()):
        s = out["by_language"][lang]
        n = len(by_lang[lang])
        print(f"{lang:<10}{n:>4}{s.get('faithfulness', 0):>16}{s.get('answer_relevancy', 0):>12}"
              f"{s.get('context_precision', 0):>12}")
    print("-" * 50)
    o = out["overall"]
    print(f"{'ALL':<10}{len(rows):>4}{o.get('faithfulness', 0):>16}"
          f"{o.get('answer_relevancy', 0):>12}{o.get('context_precision', 0):>12}")
    print("=" * 50)
    print(f"\nResults saved to: {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true",
                    help="Generate answers for eval queries (saves to --out).")
    ap.add_argument("--score", action="store_true",
                    help="Score an existing answers file with RAGAS.")
    ap.add_argument("--in", dest="in_path", type=str, default="answers.json")
    ap.add_argument("--out", type=str, default="results_generation.json")
    ap.add_argument("--max-queries", type=int, default=15)
    args = ap.parse_args()

    if args.generate:
        generate_answers(args.out, max_queries=args.max_queries)
    elif args.score:
        score_with_ragas(args.in_path, args.out)
    else:
        print("Use --generate to produce answers, or --score to evaluate them with RAGAS.")
        print("Typical flow:")
        print("  python bench/generation_eval.py --generate --out answers_baseline.json")
        print("  python bench/generation_eval.py --score --in answers_baseline.json --out results_generation_baseline.json")


if __name__ == "__main__":
    main()
