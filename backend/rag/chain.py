"""
============================================================================
rag/chain.py — LangChain RAG chain (the "framework" baseline)
============================================================================
WHY THIS EXISTS
---------------
Requirement: "Use LangChain and/or LangGraph." This module implements the
LangChain baseline — a single LCEL (LangChain Expression Language) chain
that does retrieve → prompt → LLM → parse.

If `settings.USE_LANGGRAPH=0`, `rag/my_engine.py` uses this chain directly.
If `settings.USE_LANGGRAPH=1`, it uses the state machine in `rag/graph.py`
instead. Both share the same retriever and the same prompt, so behavior is
identical — LangGraph just makes the flow explicit and debuggable.

LCEL CHAIN STRUCTURE
--------------------
    {"context": retriever, "question": RunnablePassthrough()}
        | prompt
        | llm
        | StrOutputParser()

- `retriever` is `vectorstore.as_retriever()` — calls similarity_search internally
- `prompt` is the trilingual template from `rag/prompts.py`
- `llm` is whatever `rag/llm.py` returns (OpenAI / Ollama / Stub)
- `StrOutputParser` unwraps the AIMessage to a plain string

We do NOT pass language as a filter here — the chain retrieves in any
language and relies on the prompt to answer in the requested language.
This is intentional: cross-lingual retrieval is the project's point.
"""
from __future__ import annotations
from typing import Optional

from django.conf import settings
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda

from .embeddings import get_embeddings
from .llm import get_llm
from .prompts import build_prompt, format_context
from .vectorstore import get_store


def _retrieve(question: str, *, language: Optional[str] = None, document_ids: Optional[list] = None,
              top_k: int = 5) -> list[dict]:
    """Helper used by both the chain and the LangGraph retrieve node."""
    store = get_store()
    kwargs = {"k": top_k}
    # Metadata filter: language AND/OR doc_id
    where = {}
    if language:
        where["language"] = language
    if document_ids:
        # Chroma supports `$in` on metadata values
        where["doc_id"] = {"$in": document_ids}
    if where:
        kwargs["filter"] = where
    docs: list[Document] = store.similarity_search(question, **kwargs)
    return [
        {
            "document_id": d.metadata.get("doc_id"),
            "title": d.metadata.get("title", ""),
            "page": d.metadata.get("source_page", 1),
            "snippet": d.page_content,
            "language": d.metadata.get("language", ""),
            "score": 0.0,  # filled in by my_engine.search; similarity_search doesn't return scores
        }
        for d in docs
    ]


def build_chain(language: str = "en", *, document_ids: Optional[list] = None, top_k: int = 5):
    """
    Build a fresh RAG chain for one invocation.

    We rebuild per-call because `language` and `document_ids` vary per
    question — baking them into a shared chain would require thread-safety.

    Returns a runnable that takes `{"question": str}` and returns the answer string.
    """
    llm = get_llm()
    prompt = build_prompt(language)

    def retriever_fn(input_dict):
        q = input_dict.get("question", "")
        docs = _retrieve(q, language=None,  # cross-lingual: don't filter by question language
                         document_ids=document_ids, top_k=top_k)
        return format_context(docs), docs

    chain = (
        {
            "context": RunnableLambda(retriever_fn) | (lambda x: x[0]),
            "question": RunnablePassthrough() | (lambda x: x["question"] if isinstance(x, dict) else x),
            "_retrieved": RunnableLambda(retriever_fn) | (lambda x: x[1]),
        }
        | prompt
        | llm
        | StrOutputParser()
    )
    return chain, retriever_fn


def run(question: str, *, language: str = "en", document_ids: Optional[list] = None,
        history: Optional[list] = None, top_k: int = 5) -> dict:
    """
    Convenience wrapper: build chain → invoke → return {answer, sources}.

    `history` is unused by the LangChain baseline (it's used by the LangGraph
    version) — kept in the signature so the engine calls both paths uniformly.
    """
    chain, retriever = build_chain(language, document_ids=document_ids, top_k=top_k)
    docs = retriever({"question": question})[1]
    answer = chain.invoke({"question": question})
    return {"answer": answer, "sources": docs}
