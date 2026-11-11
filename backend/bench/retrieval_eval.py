"""
============================================================================
bench/retrieval_eval.py — Retrieval quality metrics (Recall@k, MRR, nDCG)
============================================================================
WHY THIS EXISTS
---------------
Requirement: "Benchmarking — evaluation of retrieval AND generation."

This script measures the RETRIEVAL half. For each query in `eval.jsonl`:
- Call `engine.search(query, language)` → get top-k chunks
- Check which `expected_doc_ids` appear in the results
- Compute standard IR metrics

METRICS
-------
- Recall@k  : fraction of expected docs found in the top-k results
              (Are we surfacing the right documents?)
- MRR       : Mean Reciprocal Rank = 1/rank of first relevant doc
              (How high is the first hit?)
- nDCG@k    : Normalised Discounted Cumulative Gain
              (Rewards relevant docs at the top of the list, penalises late hits)

USAGE
-----
    cd backend
    python bench/retrieval_eval.py                       # uses default engine + eval.jsonl
    python bench/retrieval_eval.py --out results_baseline.json
    python bench/retrieval_eval.py --top-k 10

After fine-tuning the embedding model, re-run with the new
EMBEDDING_MODEL path and a different --out file, then compare.
"""
from __future__ import annotations
import argparse
import json
import math
import os
import sys
from pathlib import Path
from collections import defaultdict

# Bootstrap Django so we can use the engine + ORM
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


def recall_at_k(retrieved_doc_ids, expected_doc_ids, k):
    if not expected_doc_ids:
        return 0.0
    topk = retrieved_doc_ids[:k]
    hits = len(set(topk) & set(expected_doc_ids))
    return hits / len(expected_doc_ids)


def reciprocal_rank(retrieved_doc_ids, expected_doc_ids):
    for i, did in enumerate(retrieved_doc_ids, start=1):
        if did in expected_doc_ids:
            return 1.0 / i
    return 0.0


def ndcg_at_k(retrieved_doc_ids, expected_doc_ids, k):
    dcg = 0.0
    for i, did in enumerate(retrieved_doc_ids[:k], start=1):
        if did in expected_doc_ids:
            dcg += 1.0 / math.log2(i + 1)
    ideal_hits = min(len(expected_doc_ids), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, ideal_hits + 1))
    return dcg / idcg if idcg > 0 else 0.0


def run(top_k: int, language_filter: bool) -> dict:
    rows = load_eval()
    engine = get_engine()

    # per-language accumulators
    by_lang = defaultdict(lambda: {"recall": [], "mrr": [], "ndcg": []})
    per_query = []

    for row in rows:
        lang = row["language"]
        query = row["query"]
        expected = row.get("expected_doc_ids", [])
        # If language_filter is on, restrict search to the query's language
        # (simulates the MCP `search_by_language` tool). If off, retrieve across
        # all languages (cross-lingual mode — the project's headline feature).
        results = engine.search(query, user=None,
                                language=lang if language_filter else None,
                                top_k=top_k)
        retrieved = [r.get("document_id") for r in results if r.get("document_id")]

        r = recall_at_k(retrieved, expected, top_k)
        mrr = reciprocal_rank(retrieved, expected)
        ndcg = ndcg_at_k(retrieved, expected, top_k)

        by_lang[lang]["recall"].append(r)
        by_lang[lang]["mrr"].append(mrr)
        by_lang[lang]["ndcg"].append(ndcg)
        per_query.append({"id": row["id"], "language": lang,
                          "recall": r, "mrr": mrr, "ndcg": ndcg,
                          "retrieved_doc_ids": retrieved})

    summary = {}
    for lang, m in by_lang.items():
        n = len(m["recall"])
        summary[lang] = {
            "n": n,
            "recall@%d" % top_k: round(sum(m["recall"]) / n, 4) if n else 0,
            "mrr": round(sum(m["mrr"]) / n, 4) if n else 0,
            "ndcg@%d" % top_k: round(sum(m["ndcg"]) / n, 4) if n else 0,
        }

    all_recall = [v for m in by_lang.values() for v in m["recall"]]
    all_mrr = [v for m in by_lang.values() for v in m["mrr"]]
    all_ndcg = [v for m in by_lang.values() for v in m["ndcg"]]
    overall = {
        "n": len(all_recall),
        "recall@%d" % top_k: round(sum(all_recall) / len(all_recall), 4) if all_recall else 0,
        "mrr": round(sum(all_mrr) / len(all_mrr), 4) if all_mrr else 0,
        "ndcg@%d" % top_k: round(sum(all_ndcg) / len(all_ndcg), 4) if all_ndcg else 0,
    }
    return {
        "config": {"top_k": top_k, "language_filter": language_filter,
                   "embedding_model": os.environ.get("EMBEDDING_MODEL",
                       "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2")},
        "overall": overall,
        "by_language": summary,
        "per_query": per_query,
    }


def print_report(result: dict):
    print("=" * 60)
    print("RETRIEVAL BENCHMARK")
    print("=" * 60)
    print(f"Embedding model : {result['config']['embedding_model']}")
    print(f"Top-k           : {result['config']['top_k']}")
    print(f"Language filter : {result['config']['language_filter']}")
    print("-" * 60)
    print(f"{'Language':<10}{'N':>4}{'Recall@k':>12}{'MRR':>10}{'nDCG@k':>12}")
    print("-" * 60)
    for lang in sorted(result["by_language"].keys()):
        s = result["by_language"][lang]
        rk = "recall@%d" % result["config"]["top_k"]
        nk = "ndcg@%d" % result["config"]["top_k"]
        print(f"{lang:<10}{s['n']:>4}{s[rk]:>12}{s['mrr']:>10}{s[nk]:>12}")
    print("-" * 60)
    o = result["overall"]
    rk = "recall@%d" % result["config"]["top_k"]
    nk = "ndcg@%d" % result["config"]["top_k"]
    print(f"{'ALL':<10}{o['n']:>4}{o[rk]:>12}{o['mrr']:>10}{o[nk]:>12}")
    print("=" * 60)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--language-filter", action="store_true",
                    help="Restrict search to the query's language (vs. cross-lingual).")
    ap.add_argument("--out", type=str, default=None,
                    help="Path to save JSON results (default: bench/results_retrieval.json)")
    args = ap.parse_args()

    result = run(top_k=args.top_k, language_filter=args.language_filter)
    print_report(result)

    out_path = args.out or str(Path(__file__).parent / "results_retrieval.json")
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    main()
