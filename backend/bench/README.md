# `bench/` — Retrieval + generation benchmark

Evaluates the RAG pipeline on two axes:
1. **Retrieval** — are the right documents surfaced? (`retrieval_eval.py`)
2. **Generation** — is the answer good? (`generation_eval.py`)

## Files

| File | What it does |
|---|---|
| `eval.jsonl` | 15 trilingual benchmark queries (5 per language) with `expected_doc_ids`, `expected_keywords`, `reference_answer` |
| `retrieval_eval.py` | Computes Recall@k, MRR, nDCG@k — per language + overall |
| `generation_eval.py` | Generates answers for eval queries, then scores them with RAGAS (`faithfulness`, `answer_relevancy`, `context_precision`) |
| `run_all.sh` | Convenience runner: `bash bench/run_all.sh baseline` or `bash bench/run_all.sh finetuned` |

## Usage

```bash
cd backend

# Baseline (default embedding model):
bash bench/run_all.sh baseline

# After fine-tuning:
EMBEDDING_MODEL=./models/docassist-ft bash bench/run_all.sh finetuned
```

## Outputs

- `bench/results_retrieval_baseline.json`
- `bench/answers_baseline.json`
- `bench/results_generation_baseline.json`
- (and `_finetuned` variants)

## Comparison

The JSON files have the same shape. To produce the before/after chart for the admin dashboard:

```python
import json
base = json.load(open("bench/results_retrieval_baseline.json"))
ft = json.load(open("bench/results_retrieval_finetuned.json"))
for lang in ["ar", "fr", "en"]:
    print(lang, base["by_language"][lang]["recall@5"], "→", ft["by_language"][lang]["recall@5"])
```

## Extending the eval set

Add queries to `eval.jsonl` (one JSON object per line). The expected_doc_ids must match Document IDs in your DB — so populate the sample docs first, then check their IDs in `/api/documents/`.
