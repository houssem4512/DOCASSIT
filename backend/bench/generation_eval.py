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

    Includes a 3-second delay between queries to respect Groq's free-tier
    rate limit (1000 output tokens per minute).
    """
    import time
    rows = load_eval()[:max_queries]
    engine = get_engine()
    results = []
    for i, r in enumerate(rows):
        print(f"[generate] {r['id']} ({r['language']}) — {r['query'][:50]}")
        try:
            resp = engine.answer(r["query"], user=None, language=r["language"])
            results.append({
                "id": r["id"],
                "language": r["language"],
                "question": r["query"],
                "answer": resp["answer"],
                "contexts": [s["snippet"] for s in resp.get("sources", [])],
                "reference": r.get("reference_answer", ""),
            })
        except Exception as e:
            print(f"  ⚠ Error on {r['id']}: {e}")
            print(f"  Waiting 30 seconds for rate limit to reset...")
            time.sleep(30)
            # Retry once
            try:
                resp = engine.answer(r["query"], user=None, language=r["language"])
                results.append({
                    "id": r["id"],
                    "language": r["language"],
                    "question": r["query"],
                    "answer": resp["answer"],
                    "contexts": [s["snippet"] for s in resp.get("sources", [])],
                    "reference": r.get("reference_answer", ""),
                })
            except Exception as e2:
                print(f"  ✗ Failed twice on {r['id']}: {e2}")
                results.append({
                    "id": r["id"],
                    "language": r["language"],
                    "question": r["query"],
                    "answer": f"(error: {e2})",
                    "contexts": [],
                    "reference": r.get("reference_answer", ""),
                })
        # Rate limit protection: 3 sec between queries
        if i < len(rows) - 1:
            time.sleep(3)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\nSaved {len(results)} answers to {out_path}")


def score_with_ragas(in_path: str, out_path: str):
    """Run RAGAS over the generated answers.

    Handles ragas 0.4.x API where metric classes require an `llm` argument.
    Creates a Groq LLM judge (same model as the RAG engine) and wraps it
    with LangchainLLMWrapper for RAGAS.
    """
    from django.conf import settings as dj_settings

    # Build the LLM judge (uses Groq since that's our configured provider)
    if not dj_settings.GROQ_API_KEY:
        print("ERROR: RAGAS scoring needs LLM_PROVIDER != none.")
        print("Set GROQ_API_KEY in your .env and retry.")
        return

    try:
        from langchain_groq import ChatGroq
        judge_llm = ChatGroq(
            model=dj_settings.GROQ_MODEL,
            api_key=dj_settings.GROQ_API_KEY,
            temperature=0.0,  # deterministic for judging
            max_tokens=256,   # short judgments — stays under rate limits
        )
    except Exception as e:
        print(f"Failed to create Groq LLM judge: {e}")
        return

    try:
        from ragas import evaluate
        from datasets import Dataset
    except ImportError as e:
        print(f"RAGAS is not installed: {e}")
        print("Run: pip install ragas datasets")
        return

    # ragas 0.4.x: metric classes need an LLM wrapper
    metrics_list = None
    metric_names = ["faithfulness", "answer_relevancy", "context_precision"]

    try:
        # Try the new ragas 0.4+ API with LLM wrapper
        from ragas.llms import LangchainLLMWrapper
        from ragas.metrics import Faithfulness, AnswerRelevancy, ContextPrecision
        wrapped = LangchainLLMWrapper(judge_llm)
        metrics_list = [
            Faithfulness(llm=wrapped),
            AnswerRelevancy(llm=wrapped),
            ContextPrecision(llm=wrapped),
        ]
        print("[score] Using ragas 0.4+ API with Groq LLM judge")
    except (ImportError, TypeError) as e:
        print(f"[score] New API failed ({e}), trying old API...")
        try:
            # Old ragas <0.4 API (pre-instantiated singletons)
            from ragas.metrics import faithfulness, answer_relevancy, context_precision
            metrics_list = [faithfulness, answer_relevancy, context_precision]
            print("[score] Using old ragas API (pre-instantiated metrics)")
        except ImportError:
            pass

    if metrics_list is None:
        print("ERROR: Could not initialize RAGAS metrics with any API version.")
        print("Falling back to simple LLM-as-judge evaluation...")
        return simple_llm_judge(in_path, out_path, judge_llm)

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
        result = evaluate(ds, metrics=metrics_list, llm=wrapped if 'wrapped' in dir() else None)
    except Exception as e:
        print(f"RAGAS evaluate failed: {e}")
        print("Falling back to simple LLM-as-judge evaluation...")
        return simple_llm_judge(in_path, out_path, judge_llm)

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


def simple_llm_judge(in_path: str, out_path: str, judge_llm):
    """Fallback: simple LLM-as-judge evaluation when RAGAS API fails.

    For each answer, asks the LLM to score it 0-1 on:
    - faithfulness (is every claim supported by the context?)
    - answer_relevancy (does it address the question?)
    - context_precision (were the retrieved chunks useful?)

    Less sophisticated than RAGAS but works with any LLM and any ragas version.
    """
    import time
    from langchain_core.messages import HumanMessage, SystemMessage

    with open(in_path, encoding="utf-8") as f:
        rows = json.load(f)

    print(f"[judge] Evaluating {len(rows)} answers with simple LLM-as-judge...")
    results = []

    for i, r in enumerate(rows):
        print(f"[judge] {r['id']} ({r['language']})...")
        context = "\n\n".join(r.get("contexts", []))[:1500] or "(no context retrieved)"

        prompt = f"""You are an evaluator. Score the answer on 3 criteria from 0.0 to 1.0.

QUESTION: {r['question']}

RETRIEVED CONTEXT:
{context}

ANSWER:
{r['answer']}

Score each criterion (0.0 = worst, 1.0 = best):
1. faithfulness: Is every claim in the answer supported by the context? (no hallucination)
2. answer_relevancy: Does the answer directly address the question?
3. context_precision: Were the retrieved chunks useful for answering?

Respond in EXACTLY this format (no other text):
faithfulness: <score>
answer_relevancy: <score>
context_precision: <score>"""

        try:
            resp = judge_llm.invoke([SystemMessage(content="You are a strict but fair evaluator."),
                                      HumanMessage(content=prompt)])
            text = resp.content if hasattr(resp, "content") else str(resp)
            scores = {}
            for line in text.split("\n"):
                line = line.strip().lower()
                for metric in ["faithfulness", "answer_relevancy", "context_precision"]:
                    if line.startswith(metric):
                        try:
                            val = float(line.split(":")[-1].strip().split()[0])
                            scores[metric] = max(0.0, min(1.0, val))
                        except (ValueError, IndexError):
                            pass
            # Default if parsing failed
            for m in ["faithfulness", "answer_relevancy", "context_precision"]:
                if m not in scores:
                    scores[m] = 0.5
            results.append({"id": r["id"], "language": r["language"], **scores})
        except Exception as e:
            print(f"  ⚠ Error: {e}")
            results.append({"id": r["id"], "language": r["language"],
                            "faithfulness": 0.5, "answer_relevancy": 0.5, "context_precision": 0.5})
        # Rate limit protection
        if i < len(rows) - 1:
            time.sleep(3)

    # Aggregate
    from collections import defaultdict
    by_lang = defaultdict(list)
    for r in results:
        by_lang[r["language"]].append(r)

    out = {
        "overall": {
            "faithfulness": round(sum(r["faithfulness"] for r in results) / len(results), 4),
            "answer_relevancy": round(sum(r["answer_relevancy"] for r in results) / len(results), 4),
            "context_precision": round(sum(r["context_precision"] for r in results) / len(results), 4),
        },
        "by_language": {},
        "answers": rows,
        "method": "simple_llm_judge (RAGAS fallback)",
    }
    for lang, items in by_lang.items():
        out["by_language"][lang] = {
            "faithfulness": round(sum(r["faithfulness"] for r in items) / len(items), 4),
            "answer_relevancy": round(sum(r["answer_relevancy"] for r in items) / len(items), 4),
            "context_precision": round(sum(r["context_precision"] for r in items) / len(items), 4),
        }

    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=2, ensure_ascii=False)

    print("\n" + "=" * 60)
    print("GENERATION BENCHMARK (Simple LLM-as-Judge)")
    print("=" * 60)
    print(f"{'Language':<10}{'N':>4}{'faithfulness':>16}{'relevancy':>12}{'ctx_prec':>12}")
    print("-" * 60)
    for lang in sorted(out["by_language"].keys()):
        s = out["by_language"][lang]
        n = len(by_lang[lang])
        print(f"{lang:<10}{n:>4}{s['faithfulness']:>16}{s['answer_relevancy']:>12}{s['context_precision']:>12}")
    print("-" * 60)
    o = out["overall"]
    print(f"{'ALL':<10}{len(results):>4}{o['faithfulness']:>16}{o['answer_relevancy']:>12}{o['context_precision']:>12}")
    print("=" * 60)
    print(f"\nResults saved to: {out_path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--generate", action="store_true",
                    help="Generate answers for eval queries (saves to --out).")
    ap.add_argument("--score", action="store_true",
                    help="Score an existing answers file (uses simple LLM-as-judge with Groq).")
    ap.add_argument("--ragas", action="store_true",
                    help="Use RAGAS instead of simple judge (experimental, may fail).")
    ap.add_argument("--in", dest="in_path", type=str, default="answers.json")
    ap.add_argument("--out", type=str, default="results_generation.json")
    ap.add_argument("--max-queries", type=int, default=15)
    args = ap.parse_args()

    if args.generate:
        generate_answers(args.out, max_queries=args.max_queries)
    elif args.score:
        if args.ragas:
            score_with_ragas(args.in_path, args.out)
        else:
            # Default: use simple LLM-as-judge (more reliable than RAGAS 0.4.x)
            from django.conf import settings as dj_settings
            if not dj_settings.GROQ_API_KEY:
                print("ERROR: Set GROQ_API_KEY in your .env first.")
                return
            from langchain_groq import ChatGroq
            judge = ChatGroq(
                model=dj_settings.GROQ_MODEL,
                api_key=dj_settings.GROQ_API_KEY,
                temperature=0.0,
                max_tokens=256,
            )
            simple_llm_judge(args.in_path, args.out, judge)
    else:
        print("Use --generate to produce answers, or --score to evaluate them.")
        print("Typical flow:")
        print("  python bench/generation_eval.py --generate --out answers_baseline.json")
        print("  python bench/generation_eval.py --score --in answers_baseline.json --out results_generation_baseline.json")
        print("")
        print("Add --ragas to use RAGAS instead of the simple judge (experimental).")


if __name__ == "__main__":
    main()

