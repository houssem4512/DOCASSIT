"""
============================================================================
bench/compare_providers.py — Latency + quality comparison across LLM providers
============================================================================
WHY THIS EXISTS
---------------
You asked: "Groq vs Ollama — which should I use?" The answer depends on your
hardware, your network, and what you value (latency, cost, privacy).

This script runs the SAME question through every provider you have configured
(Groq / OpenAI / Ollama) and prints:
- Time to first token (latency)
- Total response time
- Tokens generated / second (throughput)
- The actual answer text (so you can eyeball quality)

USAGE
-----
    cd backend
    # Run all providers you have keys for (skips the ones missing keys):
    python bench/compare_providers.py --question "ما هو الذكاء الاصطناعي؟"

    # Force a specific list:
    python bench/compare_providers.py --providers groq ollama --question "Qu'est-ce que le climat ?"

    # Use a built-in trilingual test set:
    python bench/compare_providers.py --preset

REQUIREMENTS
------------
- Groq    : export GROQ_API_KEY=gsk_...
- OpenAI  : export OPENAI_API_KEY=sk-...
- Ollama  : ollama serve  (in another terminal) + ollama pull qwen2.5:7b
"""
from __future__ import annotations
import argparse
import json
import os
import sys
import time
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BACKEND_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django  # noqa: E402
django.setup()

from django.conf import settings  # noqa: E402
from langchain_core.messages import HumanMessage, SystemMessage  # noqa: E402

PRESET_QUESTIONS = [
    ("ar", "ما هو الذكاء الاصطناعي؟"),
    ("fr", "Qu'est-ce que le changement climatique ?"),
    ("en", "What is the history of the Internet?"),
]

SYSTEM_PROMPT = (
    "You are a multilingual assistant. Answer the user's question in the same "
    "language as the question. Keep the answer under 100 words."
)


def _build_llm_for(provider: str):
    """Build a fresh LLM for a specific provider (bypassing the singleton)."""
    if provider == "groq":
        if not settings.GROQ_API_KEY:
            return None, "GROQ_API_KEY not set"
        from langchain_groq import ChatGroq
        return ChatGroq(model=settings.GROQ_MODEL, api_key=settings.GROQ_API_KEY,
                        temperature=0.2, max_tokens=256), "ok"
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            return None, "OPENAI_API_KEY not set"
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(model=settings.OPENAI_MODEL, api_key=settings.OPENAI_API_KEY,
                          temperature=0.2, max_tokens=256), "ok"
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(model=settings.OLLAMA_MODEL, base_url=settings.OLLAMA_BASE_URL,
                          temperature=0.2, num_predict=256), "ok"
    return None, f"unknown provider: {provider}"


def run_one(llm, question: str) -> dict:
    """Run one question through one LLM, timing everything."""
    messages = [SystemMessage(content=SYSTEM_PROMPT), HumanMessage(content=question)]
    t0 = time.perf_counter()
    try:
        resp = llm.invoke(messages)
    except Exception as e:
        return {"error": f"{type(e).__name__}: {e}", "elapsed_s": time.perf_counter() - t0}
    elapsed = time.perf_counter() - t0
    answer = resp.content if hasattr(resp, "content") else str(resp)
    # rough token count: split on whitespace (good enough for comparison)
    tokens = max(1, len(answer.split()))
    return {
        "answer": answer,
        "elapsed_s": round(elapsed, 2),
        "tokens": tokens,
        "tokens_per_sec": round(tokens / elapsed, 1) if elapsed > 0 else 0,
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--question", type=str, default=None,
                    help="Single question to ask each provider.")
    ap.add_argument("--lang", type=str, default="en",
                    help="Language code of the question (ar/fr/en).")
    ap.add_argument("--providers", nargs="+", default=["groq", "openai", "ollama"],
                    help="Providers to test (default: groq openai ollama).")
    ap.add_argument("--preset", action="store_true",
                    help="Use the built-in 3-question trilingual preset.")
    ap.add_argument("--out", type=str, default=None,
                    help="Save JSON results to this path.")
    args = ap.parse_args()

    if args.preset:
        questions = PRESET_QUESTIONS
    elif args.question:
        questions = [(args.lang, args.question)]
    else:
        ap.print_help()
        print("\n--preset or --question required.")
        return

    all_results = []
    for provider in args.providers:
        llm, status = _build_llm_for(provider)
        if llm is None:
            print(f"\n[skip] {provider}: {status}")
            continue
        print(f"\n{'=' * 60}\n  {provider.upper()}  (model: {getattr(llm, 'model_name', getattr(llm, 'model', '?'))})\n{'=' * 60}")
        for lang, q in questions:
            print(f"\n  Q ({lang}): {q}")
            r = run_one(llm, q)
            if "error" in r:
                print(f"  ✗ ERROR: {r['error']}  ({r['elapsed_s']}s)")
            else:
                print(f"  ✓ {r['elapsed_s']}s  |  {r['tokens']} tokens  |  {r['tokens_per_sec']} tok/s")
                print(f"  A: {r['answer'][:200]}{'...' if len(r['answer']) > 200 else ''}")
            r["provider"] = provider
            r["language"] = lang
            r["question"] = q
            all_results.append(r)

    # Summary table
    print(f"\n{'=' * 60}\n  SUMMARY\n{'=' * 60}")
    print(f"  {'Provider':<10}{'Question':<30}{'Time(s)':>10}{'Tok/s':>10}")
    print(f"  {'-' * 60}")
    for r in all_results:
        if "error" in r:
            continue
        q_short = r["question"][:28]
        print(f"  {r['provider']:<10}{q_short:<30}{r['elapsed_s']:>10}{r['tokens_per_sec']:>10}")

    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(all_results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved to: {args.out}")


if __name__ == "__main__":
    main()
