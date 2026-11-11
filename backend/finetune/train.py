"""
============================================================================
finetune/train.py — Fine-tune the multilingual embedding model
============================================================================
WHY THIS EXISTS
---------------
Requirement: "Compare a multilingual embedding model BEFORE and AFTER training."

This script fine-tunes `paraphrase-multilingual-MiniLM-L12-v2` on the
(query, positive_chunk) pairs in `triples.jsonl`, using the
MultipleNegativesRankingLoss — the standard contrastive loss for retrieval.

The fine-tuned model is saved to `./models/docassist-ft`. Point
`EMBEDDING_MODEL` env var at this path and re-run `bench/run_all.sh` to
get the "after" benchmark numbers.

LOSS EXPLANATION
----------------
`MultipleNegativesRankingLoss` takes (anchor, positive) pairs and treats
all other positives in the batch as negatives. For a batch of 16, each
anchor sees 1 positive + 15 negatives. This is highly efficient — no need
to manually mine hard negatives — and works very well for retrieval.

WHAT YOU NEED
-------------
- A GPU is recommended (Colab T4 works fine). On CPU, 3 epochs take ~30 min
  for 200 triples.
- The triples file (`triples.jsonl`) — extend it with your own data for
  better results. Aim for 200–500 triples per language.

USAGE
-----
    cd backend
    python finetune/train.py --epochs 3 --batch-size 16
    # After training:
    EMBEDDING_MODEL=./models/docassist-ft python bench/run_all.sh finetuned

You can also run this in a Jupyter / Colab notebook — just paste the code
below into a cell and execute.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

from torch.utils.data import DataLoader
from sentence_transformers import (
    SentenceTransformer,
    InputExample,
    losses,
)


TRIPLES_PATH = Path(__file__).parent / "triples.jsonl"
DEFAULT_BASE = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_OUT = Path(__file__).resolve().parent.parent / "models" / "docassist-ft"


def load_examples(path: Path) -> list[InputExample]:
    """
    Each line of triples.jsonl:
        {"query": "...", "positive": "...", "negative": "..."}

    We use (query, positive) pairs. The `negative` field is unused by
    MultipleNegativesRankingLoss — it uses in-batch negatives instead.
    """
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            examples.append(InputExample(texts=[r["query"], r["positive"]]))
    print(f"Loaded {len(examples)} (query, positive) pairs from {path}")
    return examples


def train(
    base_model: str = DEFAULT_BASE,
    out_dir: Path = DEFAULT_OUT,
    epochs: int = 3,
    batch_size: int = 16,
    warmup_steps: int = 50,
):
    """
    Run fine-tuning.

    Args:
        base_model:    HuggingFace model name or local path.
        out_dir:       Where to save the fine-tuned model.
        epochs:        3 is a good default for small datasets.
        batch_size:    16 fits comfortably on a T4 (16GB). Use 8 on CPU.
        warmup_steps:  Linear warmup before the main learning rate.
    """
    print(f"[1/4] Loading base model: {base_model}")
    model = SentenceTransformer(base_model)

    print("[2/4] Loading training data...")
    examples = load_examples(TRIPLES_PATH)
    if len(examples) < 4:
        raise ValueError(
            f"Need at least 4 examples for meaningful training, got {len(examples)}. "
            "Extend finetune/triples.jsonl."
        )
    loader = DataLoader(examples, shuffle=True, batch_size=batch_size, drop_last=True)

    print("[3/4] Setting up MultipleNegativesRankingLoss...")
    loss = losses.MultipleNegativesRankingLoss(model)

    print(f"[4/4] Training {epochs} epochs, batch_size={batch_size}...")
    model.fit(
        train_objectives=[(loader, loss)],
        epochs=epochs,
        warmup_steps=warmup_steps,
        show_progress_bar=True,
        optimizer_params={"lr": 2e-5},
        weight_decay=0.01,
    )

    out_dir.mkdir(parents=True, exist_ok=True)
    model.save(str(out_dir))
    print(f"\n✓ Fine-tuned model saved to: {out_dir}")
    print("\nNext steps:")
    print(f"  1. Set EMBEDDING_MODEL={out_dir}")
    print("  2. Restart the Django server (so the new model loads)")
    print("  3. Re-run: bash bench/run_all.sh finetuned")
    print("  4. Compare bench/results_*_baseline.json vs bench/results_*_finetuned.json")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--base-model", type=str, default=DEFAULT_BASE,
                    help="HuggingFace model name to fine-tune")
    ap.add_argument("--out", type=str, default=str(DEFAULT_OUT),
                    help="Output directory for the fine-tuned model")
    ap.add_argument("--epochs", type=int, default=3)
    ap.add_argument("--batch-size", type=int, default=16)
    ap.add_argument("--warmup", type=int, default=50)
    args = ap.parse_args()

    train(
        base_model=args.base_model,
        out_dir=Path(args.out),
        epochs=args.epochs,
        batch_size=args.batch_size,
        warmup_steps=args.warmup,
    )


if __name__ == "__main__":
    main()
