"""
============================================================================
rag/prompts.py — Trilingual RAG prompt templates
============================================================================
WHY THIS EXISTS
---------------
A multilingual assistant must answer in the user's language even when the
retrieved documents are in a different language. Example: the user asks in
Arabic, the retrieved chunks are French — the LLM must translate and answer
in Arabic, citing the French source.

This is the heart of "search in one language, ask in another".

PROMPT STRUCTURE
----------------
Three sections:
1. ROLE       — "You are a multilingual document assistant..."
2. RULES      — answer in `language`, use only the context, cite by [title, p.X]
3. CONTEXT    — the retrieved chunks (numbered for easy citation)
4. QUESTION   — the user's question

The prompt is the same logic in all three languages so the LLM doesn't get
confused by mixed-language instructions.
"""
from __future__ import annotations
from langchain_core.prompts import ChatPromptTemplate

# ---------- System / instruction text, trilingual ----------

SYSTEMS = {
    "ar": (
        "أنت مساعد وثائق متعدد اللغات. مهمتك: الإجابة على السؤال بالاعتماد الحصري على السياق المُسترجَع.\n"
        "القواعد:\n"
        "1. أجب بالعربية فقط، حتى لو كانت الوثائق بلغة أخرى.\n"
        "2. لا تخترع معلومات غير موجودة في السياق.\n"
        "3. اذكر المصدر بصيغة: [عنوان الوثيقة، ص. X] في نهاية كل معلومة.\n"
        "4. إذا لم يكن السياق كافياً، قل: \"لا توجد معلومات كافية في الوثائق\".\n"
    ),
    "fr": (
        "Vous êtes un assistant documentaire multilingue. Votre tâche : répondre à la question en vous appuyant exclusivement sur le contexte récupéré.\n"
        "Règles :\n"
        "1. Répondez en français uniquement, même si les documents sont dans une autre langue.\n"
        "2. N'inventez aucune information absente du contexte.\n"
        "3. Citez la source sous la forme : [titre du document, p. X] à la fin de chaque information.\n"
        "4. Si le contexte est insuffisant, dites : « Les documents ne contiennent pas assez d'informations ».\n"
    ),
    "en": (
        "You are a multilingual document assistant. Your task: answer the question using exclusively the retrieved context.\n"
        "Rules:\n"
        "1. Answer in English only, even if the documents are in another language.\n"
        "2. Do not invent information not present in the context.\n"
        "3. Cite the source as: [document title, p. X] at the end of each fact.\n"
        "4. If the context is insufficient, say: \"The documents do not contain enough information\".\n"
    ),
}


def format_context(chunks: list[dict]) -> str:
    """
    Turn retrieved chunks into a numbered context block.

    Each chunk: {"title": str, "page": int, "snippet": str, "language": str}

    Returns text like:
        [1] (title, p.3) <snippet>
        [2] (title, p.5) <snippet>
        ...
    The numbers let the LLM cite cleanly: "according to [2]..."
    """
    if not chunks:
        return "(no context retrieved)"
    lines = []
    for i, c in enumerate(chunks, start=1):
        title = c.get("title", "?")
        page = c.get("page", c.get("source_page", "?"))
        snippet = c.get("snippet", c.get("text", ""))[:800]
        lines.append(f"[{i}] ({title}, p.{page})\n{snippet}")
    return "\n\n".join(lines)


def build_prompt(language: str) -> ChatPromptTemplate:
    """
    Returns a LangChain ChatPromptTemplate with 3 message slots:
      - system  : the rules in `language`
      - human   : the retrieved context (passed at invoke time as `context`)
      - human   : the question (passed at invoke time as `question`)
    """
    sys = SYSTEMS.get(language, SYSTEMS["en"])
    return ChatPromptTemplate.from_messages([
        ("system", sys),
        ("human", "CONTEXT:\n{context}\n\nQUESTION:\n{question}"),
    ])
