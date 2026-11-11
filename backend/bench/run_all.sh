#!/usr/bin/env bash
# ============================================================
# bench/run_all.sh — Run the full benchmark suite
# ============================================================
# Usage:
#   cd backend
#   bash bench/run_all.sh                  # baseline (default embedding model)
#   bash bench/run_all.sh finetuned        # after fine-tuning (set EMBEDDING_MODEL path)
#
# Output files:
#   bench/results_retrieval_baseline.json
#   bench/answers_baseline.json
#   bench/results_generation_baseline.json
# (or _finetuned suffix)
# ============================================================
set -e
cd "$(dirname "$0")/.."   # backend/

SUFFIX="${1:-baseline}"

echo "============================================================"
echo "  RAG BENCHMARK — $SUFFIX"
echo "============================================================"
echo "Embedding model: ${EMBEDDING_MODEL:-default}"
echo "LLM provider   : ${LLM_PROVIDER:-none}"
echo ""

echo "[1/3] Retrieval benchmark..."
python bench/retrieval_eval.py --top-k 5 --out "bench/results_retrieval_${SUFFIX}.json"

echo ""
echo "[2/3] Generating answers..."
python bench/generation_eval.py --generate --out "bench/answers_${SUFFIX}.json" --max-queries 15

if [ "${LLM_PROVIDER:-none}" != "none" ]; then
  echo ""
  echo "[3/3] Scoring answers with RAGAS..."
  python bench/generation_eval.py --score \
    --in "bench/answers_${SUFFIX}.json" \
    --out "bench/results_generation_${SUFFIX}.json"
else
  echo ""
  echo "[3/3] SKIPPED: RAGAS scoring requires LLM_PROVIDER != none."
  echo "          Set LLM_PROVIDER=openai (with OPENAI_API_KEY) and re-run."
fi

echo ""
echo "============================================================"
echo "  DONE — compare bench/results_*_${SUFFIX}.json"
echo "============================================================"
