"""rag package — trilingual RAG pipeline for the DocAssist project.

Modules
-------
- engine.py       : BaseRAGEngine contract + PlaceholderEngine + get_engine() + detect_language
- extractors.py   : PDF / DOCX / TXT / MD text extraction
- chunker.py      : LangChain RecursiveCharacterTextSplitter with metadata
- embeddings.py   : sentence-transformers wrapper (LangChain Embeddings)
- vectorstore.py  : Chroma persistent vector store
- llm.py          : LLM provider factory (none / openai / ollama)
- prompts.py      : trilingual RAG prompt templates
- chain.py        : LangChain LCEL RAG chain
- graph.py        : LangGraph state machine with tool calling
- my_engine.py    : real BaseRAGEngine implementation that ties it all together
"""
