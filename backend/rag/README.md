# `rag/` — Trilingual RAG pipeline

This is the AI layer. It plugs into the existing `BaseRAGEngine` contract defined in `engine.py`.

## Modules

| File | Role |
|---|---|
| `engine.py` | The contract (`BaseRAGEngine`) + `PlaceholderEngine` + `get_engine()` factory + `detect_language` heuristic. **Original file, unchanged.** |
| `extractors.py` | PDF / DOCX / TXT / MD → text + page count |
| `chunker.py` | LangChain `RecursiveCharacterTextSplitter` + per-chunk metadata |
| `embeddings.py` | sentence-transformers multilingual wrapper (LangChain `Embeddings`) |
| `vectorstore.py` | Chroma persistent vector store |
| `llm.py` | LLM provider factory (`none` / `openai` / `ollama`) |
| `prompts.py` | Trilingual RAG system prompts (ar / fr / en) |
| `chain.py` | LangChain LCEL RAG chain |
| `graph.py` | LangGraph state machine with tool calling |
| `my_engine.py` | Real `BaseRAGEngine` implementation — **activates the AI layer** |

## Activation

`config/settings.py` already points to the real engine:
```python
RAG_ENGINE = "rag.my_engine.MyRAGEngine"
```

To fall back to the demo stub:
```bash
RAG_ENGINE=rag.engine.PlaceholderEngine python manage.py runserver
```

## Data flow

```
upload → extractors.extract(path)
       → chunker.chunk(text, doc_id, language, title, page_texts)
       → vectorstore.add_documents(chunks)

search → vectorstore.similarity_search_with_score(query, filter={language, doc_id})
       → map to {document_id, title, page, snippet, score}

answer → graph.run(question, language, document_ids, history)
       → retrieve node (cross-lingual similarity_search)
       → generate node (trilingual prompt + LLM)
       → cite node (format sources list)
```

See `../AI_INTEGRATION_GUIDE.md` for the full walkthrough.
