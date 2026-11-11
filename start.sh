#!/usr/bin/env bash
# ============================================================
# DocAssist — quick start helper
# ============================================================
# Usage:
#   bash start.sh backend   # set up + run Django (port 8000)
#   bash start.sh frontend  # set up + run React (port 5173)
#   bash start.sh mcp       # run the MCP server (stdio)
#   bash start.sh bench     # run the baseline benchmark
#   bash start.sh finetune  # fine-tune the embedding model
# ============================================================
set -e
cd "$(dirname "$0")"
CMD="${1:-help}"

case "$CMD" in
  backend)
    cd backend
    [ -d .venv ] || python3 -m venv .venv
    source .venv/bin/activate
    pip install -q -r requirements.txt
    python manage.py migrate
    python manage.py seed_demo || true
    echo ""
    echo "============================================================"
    echo "  Backend running on http://localhost:8000"
    echo "  Admin login : admin / admin123"
    echo "  Demo login  : demo / demo1234"
    echo "  LLM_PROVIDER = ${LLM_PROVIDER:-none}  (set to openai or ollama for real answers)"
    echo "============================================================"
    python manage.py runserver
    ;;
  frontend)
    cd frontend
    [ -d node_modules ] || npm install
    echo ""
    echo "============================================================"
    echo "  Frontend running on http://localhost:5173"
    echo "============================================================"
    npm run dev
    ;;
  mcp)
    cd backend
    [ -d .venv ] && source .venv/bin/activate
    echo "Starting MCP server on stdio. Press Ctrl+C to stop."
    echo "Test interactively with:  mcp dev backend/mcp_server/server.py"
    python -m mcp_server.server
    ;;
  bench)
    cd backend
    [ -d .venv ] && source .venv/bin/activate
    bash bench/run_all.sh "${2:-baseline}"
    ;;
  finetune)
    cd backend
    [ -d .venv ] && source .venv/bin/activate
    python finetune/train.py --epochs "${2:-3}"
    echo ""
    echo "Done. Re-benchmark with:"
    echo "  EMBEDDING_MODEL=./models/docassist-ft bash bench/run_all.sh finetuned"
    ;;
  help|*)
    cat <<EOF
DocAssist — quick start helper

Commands:
  bash start.sh backend    Set up + run Django backend (port 8000)
  bash start.sh frontend   Set up + run React frontend (port 5173)
  bash start.sh mcp        Run the MCP server (stdio transport)
  bash start.sh bench      Run the baseline benchmark
                            (or: bash start.sh bench finetuned)
  bash start.sh finetune   Fine-tune the embedding model
                            (or: bash start.sh finetune 5  # 5 epochs)

Typical first run:
  bash start.sh backend    # terminal 1
  bash start.sh frontend   # terminal 2
  # open http://localhost:5173

Enable a real LLM (optional):
  # Option A — Groq (free cloud, recommended):
  export LLM_PROVIDER=groq
  export GROQ_API_KEY=gsk_...   # get one at https://console.groq.com/keys

  # Option B — OpenAI (paid):
  export LLM_PROVIDER=openai
  export OPENAI_API_KEY=sk-...

  # Option C — Ollama (local, offline):
  export LLM_PROVIDER=ollama

  bash start.sh backend
EOF
    ;;
esac
