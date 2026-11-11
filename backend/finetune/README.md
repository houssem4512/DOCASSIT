# `finetune/` — Multilingual embedding fine-tuning

Fine-tunes `paraphrase-multilingual-MiniLM-L12-v2` on (query, positive) pairs, then compares retrieval quality before and after.

## Files

| File | What it does |
|---|---|
| `triples.jsonl` | 18 starter (query, positive, negative) triples across ar/fr/en |
| `train.py` | Fine-tunes the model with `MultipleNegativesRankingLoss`, saves to `./models/docassist-ft` |
| `build_triples.py` | Auto-generates triples from indexed chunks (for scaling up) |

## Usage

```bash
cd backend

# 1. (optional) generate more triples from your indexed docs:
python finetune/build_triples.py --per-language 50 --out finetune/triples_auto.jsonl

# 2. fine-tune (3 epochs, ~15 min on T4 GPU, ~30 min on CPU):
python finetune/train.py --epochs 3 --batch-size 16

# 3. re-benchmark with the fine-tuned model:
EMBEDDING_MODEL=./models/docassist-ft bash bench/run_all.sh finetuned

# 4. compare:
#    bench/results_retrieval_baseline.json
#    vs
#    bench/results_retrieval_finetuned.json
```

## Loss function

`MultipleNegativesRankingLoss` takes (query, positive) pairs and treats all other positives in the batch as negatives. For a batch of 16, each anchor sees 1 positive + 15 negatives. This is highly efficient — no need to manually mine hard negatives — and is the standard loss for retrieval fine-tuning.

## Extending the training data

The starter `triples.jsonl` has 18 entries — fine for proving the pipeline works. For meaningful improvements, aim for 200–500 triples per language.

To generate triples automatically from your indexed chunks:
```bash
python finetune/build_triples.py --per-language 100
```

For higher-quality triples, replace `first_sentence()` in `build_triples.py` with an LLM call:
```python
# Instead of: query = first_sentence(chunk_text)
# Use:
from rag.llm import get_llm
query = get_llm().invoke(f"Generate a question whose answer is: {chunk_text}").content
```

## Hardware

- **GPU recommended** (Colab T4 is fine). 3 epochs × 200 triples ≈ 15 min on T4.
- **CPU works** for small datasets. Same run ≈ 30 min.
- The fine-tuned model is ~120 MB (same size as the base).
