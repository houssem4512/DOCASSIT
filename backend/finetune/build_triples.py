"""
============================================================================
finetune/build_triples.py — Auto-generate (query, positive, negative) triples
============================================================================
WHY THIS EXISTS
---------------
`triples.jsonl` ships with a small starter set (15 entries). For real
fine-tuning you want 200–500 triples per language. This script generates
them automatically from your indexed documents:

1. Pull all chunks per language from the Chroma vector store
2. For each chunk, treat it as the "positive" — assume it's an answer to
   some implicit question
3. Generate a question for it by truncating to the first sentence
   (cheap heuristic — for production use an LLM to generate questions)
4. Pick a random chunk from a DIFFERENT document as the "negative"

USAGE
-----
    cd backend
    python finetune/build_triples.py --out finetune/triples_auto.jsonl
    # then merge with the hand-written triples.jsonl or use it standalone

For higher-quality triples, you'd replace step 3 with an LLM call:
    "Generate a question whose answer is: <chunk text>"
The script shows where to plug that in (see TODO in code).
"""
from __future__ import annotations
import argparse
import json
import os
import random
import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402
django.setup()

from rag.vectorstore import get_store  # noqa: E402


def fetch_all_chunks():
    """Return all chunks from the vector store, grouped by language."""
    store = get_store()
    col = store._collection
    # Pull all chunks (Chroma allows get() without a query vector)
    res = col.get(include=["documents", "metadatas"])
    chunks_by_lang = {"ar": [], "fr": [], "en": []}
    for text, meta in zip(res["documents"], res["metadatas"]):
        lang = meta.get("language", "en")
        if lang not in chunks_by_lang:
            chunks_by_lang[lang] = []
        chunks_by_lang[lang].append({"text": text, "doc_id": meta.get("doc_id"),
                                      "title": meta.get("title", "")})
    return chunks_by_lang


def first_sentence(text: str, max_chars: int = 120) -> str:
    """Cheap query heuristic: take the first sentence of the chunk as the 'query'.
    For better triples, replace this with an LLM call."""
    for sep in [". ", "؟ ", "? ", "! ", "\n"]:
        idx = text.find(sep)
        if 0 < idx < max_chars:
            return text[:idx].strip()
    return text[:max_chars].strip()


def build_triples(out_path: str, per_language: int = 30):
    chunks_by_lang = fetch_all_chunks()
    triples = []
    for lang, chunks in chunks_by_lang.items():
        if len(chunks) < 2:
            print(f"[skip] language={lang} has only {len(chunks)} chunks (need ≥2)")
            continue
        n = min(per_language, len(chunks))
        for chunk in random.sample(chunks, n):
            query = first_sentence(chunk["text"])
            positive = chunk["text"]
            # negative = a chunk from a different document
            negatives = [c for c in chunks if c["doc_id"] != chunk["doc_id"]]
            if not negatives:
                continue
            neg = random.choice(negatives)
            triples.append({
                "query": query,
                "positive": positive,
                "negative": neg["text"],
                "language": lang,
            })
    random.shuffle(triples)
    with open(out_path, "w", encoding="utf-8") as f:
        for t in triples:
            f.write(json.dumps(t, ensure_ascii=False) + "\n")
    print(f"Generated {len(triples)} triples → {out_path}")
    print("\nTODO for better quality: replace `first_sentence()` with an LLM call")
    print('   e.g. llm.invoke("Generate a question whose answer is: " + chunk_text)')


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=str, default=str(Path(__file__).parent / "triples_auto.jsonl"))
    ap.add_argument("--per-language", type=int, default=30)
    args = ap.parse_args()
    build_triples(args.out, per_language=args.per_language)


if __name__ == "__main__":
    main()
