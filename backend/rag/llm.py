"""
============================================================================
rag/llm.py — Pluggable LLM provider (OpenAI / Ollama / none)
============================================================================
WHY THIS EXISTS
---------------
The project should run out of the box with zero API keys (so retrieval and
search work immediately) AND be upgradable to a real LLM when the user is
ready. This factory reads `settings.LLM_PROVIDER` and returns the right
LangChain `BaseChatModel`.

THREE MODES
-----------
1. LLM_PROVIDER=none (default)
   Returns a `StubLLM` that echoes the retrieved context back with a notice.
   This means: upload works, search works, chat returns retrieved chunks
   with a "configure an LLM provider to get a real answer" notice.
   Zero dependencies, zero cost — perfect for the first demo run.

2. LLM_PROVIDER=openai
   Uses `langchain_openai.ChatOpenAI` with `settings.OPENAI_MODEL` (default
   `gpt-4o-mini` — cheap and good for trilingual). Needs `OPENAI_API_KEY`
   env var. This is what you want for the production demo.

3. LLM_PROVIDER=ollama
   Uses `langchain_ollama.ChatOllama` against a local Ollama server
   (`http://localhost:11434`). Install Ollama from https://ollama.com and
   `ollama pull qwen2.5:7b`. Free, offline, no API key.

SINGLETON
---------
LLM clients hold connection pools — we cache one per process.
"""
from __future__ import annotations
from typing import Any

from django.conf import settings
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import AIMessage, HumanMessage


class StubLLM(BaseChatModel):
    """
    No-API-key fallback. Returns a polite notice with the retrieved context
    attached so the user can see retrieval is working.

    This is what makes the project runnable before the user configures an LLM.
    """

    @property
    def _llm_type(self) -> str:
        return "stub"

    def _generate(self, messages, stop=None, run_manager=None, **kwargs):
        # Pull the last user message and the system prompt
        last_user = ""
        context = ""
        for m in messages:
            if isinstance(m, HumanMessage):
                last_user = m.content
        # The context is embedded in the system message by `rag/prompts.py`.
        # We surface it back so the user sees retrieval is working.
        for m in messages:
            content = m.content if isinstance(m.content, str) else str(m.content)
            if "CONTEXT" in content or "context" in content.lower():
                context = content
                break
        reply = (
            "LLM_PROVIDER=none — retrieval is working but no LLM is configured.\n\n"
            f"Question received: {last_user[:200]}\n\n"
            f"Retrieved context:\n{context[:1500]}\n\n"
            "Set LLM_PROVIDER=groq (free, recommended), openai, or ollama to get real answers."
        )
        return {"generations": [{"text": reply, "message": AIMessage(content=reply)}]}


_llm: BaseChatModel | None = None


def get_llm() -> BaseChatModel:
    """Return the shared LLM client (singleton)."""
    global _llm
    if _llm is None:
        _llm = _build_llm()
    return _llm


def _build_llm() -> BaseChatModel:
    provider = settings.LLM_PROVIDER.lower()
    if provider == "openai":
        if not settings.OPENAI_API_KEY:
            raise RuntimeError(
                "LLM_PROVIDER=openai but OPENAI_API_KEY is not set. "
                "Export OPENAI_API_KEY=sk-... or switch to LLM_PROVIDER=none / ollama / groq."
            )
        from langchain_openai import ChatOpenAI
        return ChatOpenAI(
            model=settings.OPENAI_MODEL,
            api_key=settings.OPENAI_API_KEY,
            temperature=0.2,  # low temperature = more faithful to retrieved context
        )
    if provider == "groq":
        # Groq is OpenAI-compatible but uses its own endpoint + free API key.
        # Get a key at https://console.groq.com/keys (no credit card needed).
        # Free tier: 30 req/min, 14,400 req/day — plenty for development.
        if not settings.GROQ_API_KEY:
            raise RuntimeError(
                "LLM_PROVIDER=groq but GROQ_API_KEY is not set. "
                "Get a free key at https://console.groq.com/keys and: "
                "export GROQ_API_KEY=gsk_..."
            )
        from langchain_groq import ChatGroq
        return ChatGroq(
            model=settings.GROQ_MODEL,
            api_key=settings.GROQ_API_KEY,
            temperature=0.2,
            max_tokens=1024,
        )
    if provider == "ollama":
        from langchain_ollama import ChatOllama
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0.2,
        )
    # default: none
    return StubLLM()


def reset_llm() -> None:
    """Used when admin changes the LLM provider via the settings panel
    (so the next call rebuilds with the new provider)."""
    global _llm
    _llm = None
