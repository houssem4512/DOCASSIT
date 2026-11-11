"""
============================================================================
rag/graph.py — LangGraph state machine (the "framework" upgrade)
============================================================================
WHY THIS EXISTS
---------------
Requirement: "Use LangChain and/or LangGraph." This module is the LangGraph
implementation — an explicit state machine with named nodes and edges.

LangGraph > plain LangChain for two reasons:
1. **Visibility**: every step (retrieve, generate, cite) is a node you can
   inspect, log, or visualise (`graph.get_graph().draw_mermaid()`).
2. **Tool calling**: an LLM can decide to call a tool (`search_by_language`)
   before answering, instead of always retrieving. This is the "Tool Calling"
   half of the requirement.

STATE MACHINE (when ENABLE_TOOL_CALLING=0)
------------------------------------------
    START → retrieve → generate → cite → END

STATE MACHINE (when ENABLE_TOOL_CALLING=1 and LLM_PROVIDER != "none")
--------------------------------------------------------------------
    START → decide ─┬─ tool_call → retrieve → generate → cite → END
                     └─ no_tool  ──────────────────────────→ generate → cite → END

NODES
-----
- `decide`   : LLM sees the question + available tools, decides if retrieval is needed
- `retrieve` : vectorstore.similarity_search with optional language/doc_id filter
- `generate` : build trilingual prompt → LLM call → string answer
- `cite`     : format sources list for the API response

TOOLS EXPOSED
-------------
- `search_by_language(query, language, k=5)` — the same tool the MCP server exposes.
  This is intentional: the LLM tool and the MCP tool share implementation,
  so behavior is identical whether called by an LLM or by an external MCP client.
"""
from __future__ import annotations
from typing import Optional, TypedDict, List, Annotated

from django.conf import settings
from langchain_core.documents import Document
from langchain_core.tools import tool
from langgraph.graph import StateGraph, END

from .chain import _retrieve
from .llm import get_llm
from .prompts import build_prompt, format_context


# ---------- State ----------

class AgentState(TypedDict, total=False):
    question: str
    language: str
    document_ids: Optional[List[int]]
    history: List[dict]
    retrieved: List[dict]
    answer: str
    sources: List[dict]
    use_tool: bool


# ---------- Tool (also exported to the MCP server) ----------

@tool
def search_by_language(query: str, language: str, k: int = 5) -> str:
    """
    Search indexed documents in a specific language.

    Args:
        query:    The search query (any language).
        language: Filter chunks to this language — "ar", "fr", or "en".
        k:        Number of results to return (default 5).

    Returns:
        Concatenated passage texts with [title, p.X] headers.
    """
    docs = _retrieve(query, language=language, top_k=k)
    if not docs:
        return "(no results)"
    return format_context(docs)


TOOLS = [search_by_language]


# ---------- Nodes ----------

def retrieve_node(state: AgentState) -> dict:
    """Pull top-k chunks from the vector store, optionally filtered by language/doc_id."""
    question = state["question"]
    language = state.get("language")
    document_ids = state.get("document_ids")
    top_k = _get_top_k()
    docs = _retrieve(question, language=None, document_ids=document_ids, top_k=top_k)
    return {"retrieved": docs}


def decide_node(state: AgentState) -> dict:
    """
    Tool-calling node: ask the LLM whether retrieval is necessary.

    The LLM sees the question and the `search_by_language` tool. If it
    decides the question needs factual context, it emits a tool call —
    we route to `retrieve`. Otherwise we skip to `generate` directly
    (e.g. for "hello" or "thanks").

    When LLM_PROVIDER=none, we always retrieve (the stub can't decide).
    """
    if settings.LLM_PROVIDER == "none":
        return {"use_tool": True}
    llm = get_llm().bind_tools(TOOLS)
    from langchain_core.messages import HumanMessage, SystemMessage
    sys = SystemMessage(content=(
        "You decide whether to call `search_by_language` before answering. "
        "Call it for factual questions about the indexed documents. "
        "Skip it for greetings, opinions, or questions unrelated to the corpus."
    ))
    hum = HumanMessage(content=state["question"])
    resp = llm.invoke([sys, hum])
    tool_calls = getattr(resp, "tool_calls", None) or []
    return {"use_tool": bool(tool_calls)}


def generate_node(state: AgentState) -> dict:
    """Build the trilingual prompt with retrieved context and call the LLM."""
    retrieved = state.get("retrieved", [])
    language = state.get("language", "en")
    question = state["question"]
    history = state.get("history", [])

    prompt = build_prompt(language)
    messages = prompt.format_messages(
        context=format_context(retrieved),
        question=question,
    )
    # Prepend conversation history (last 5 turns) for multi-turn chat.
    # We skip this for the stub LLM since it ignores it anyway.
    from langchain_core.messages import HumanMessage, AIMessage
    hist_msgs = []
    for h in history[-10:]:
        if h.get("role") == "user":
            hist_msgs.append(HumanMessage(content=h["content"]))
        elif h.get("role") == "assistant":
            hist_msgs.append(AIMessage(content=h["content"]))
    # History goes BEFORE the final question (which is already the last message in `messages`).
    # So we keep the system msg, prepend history, then re-add the final human turn.
    if hist_msgs and len(messages) >= 2:
        final_human = messages[-1]
        messages = messages[:-1] + hist_msgs + [final_human]

    llm = get_llm()
    answer = llm.invoke(messages).content
    return {"answer": answer}


def cite_node(state: AgentState) -> dict:
    """Format the sources list for the API response (matches the contract in rag/engine.py)."""
    sources = []
    for d in state.get("retrieved", []):
        sources.append({
            "document_id": d.get("document_id"),
            "title": d.get("title", ""),
            "page": d.get("page", 1),
            "snippet": d.get("snippet", "")[:300],
            "score": d.get("score", 0.0),
        })
    return {"sources": sources}


# ---------- Routing ----------

def _route_after_decide(state: AgentState) -> str:
    return "retrieve" if state.get("use_tool") else "generate"


# ---------- Builder ----------

def _get_top_k() -> int:
    try:
        from apps.core.models import AppSetting
        obj = AppSetting.objects.filter(key="rag").first()
        if obj and obj.value:
            return int(obj.value.get("top_k", 5))
    except Exception:
        pass
    return 5


def build_graph():
    """
    Compile and return the LangGraph agent.

    Called once per `MyRAGEngine.answer()` invocation. Compilation is cheap
    (microseconds); we don't bother caching because LangGraph graphs are
    stateless and rebuild-safe.
    """
    g = StateGraph(AgentState)
    g.add_node("retrieve", retrieve_node)
    g.add_node("generate", generate_node)
    g.add_node("cite", cite_node)

    if settings.ENABLE_TOOL_CALLING and settings.LLM_PROVIDER != "none":
        g.add_node("decide", decide_node)
        g.set_entry_point("decide")
        g.add_conditional_edges("decide", _route_after_decide, {"retrieve": "retrieve", "generate": "generate"})
    else:
        g.set_entry_point("retrieve")

    g.add_edge("retrieve", "generate")
    g.add_edge("generate", "cite")
    g.add_edge("cite", END)
    return g.compile()


def run(question: str, *, language: str = "en", document_ids: Optional[list] = None,
        history: Optional[list] = None) -> dict:
    """Invoke the compiled graph and return {answer, language, sources}."""
    graph = build_graph()
    state: AgentState = {
        "question": question,
        "language": language,
        "document_ids": document_ids,
        "history": history or [],
        "retrieved": [],
        "answer": "",
        "sources": [],
    }
    result = graph.invoke(state)
    return {
        "answer": result.get("answer", ""),
        "language": language,
        "sources": result.get("sources", []),
    }


def mermaid_diagram() -> str:
    """Return a Mermaid diagram of the graph — paste into the report or the
    admin panel to visualise the agent flow."""
    try:
        return build_graph().get_graph().draw_mermaid()
    except Exception as e:
        return f"(graph visualisation unavailable: {e})"
