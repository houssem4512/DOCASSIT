# `mcp_server/` — Model Context Protocol server

Exposes the DocAssist RAG engine as 3 MCP tools so external LLM clients (Claude Desktop, Cursor, etc.) can ingest documents, search by language, and ask questions with citations — without going through the Django HTTP API.

## Tools

| Tool | Args | Returns |
|---|---|---|
| `ingest_document` | `file_path: str`, `language: str?` | `{status, pages, language, error, chunks_indexed}` |
| `search_by_language` | `query: str`, `language: str`, `k: int=5` | list of `{document_id, title, page, snippet, score}` |
| `answer_with_citations` | `query: str`, `language: str?` | `{answer, language, sources[]}` |
| `list_indexed_languages` (bonus) | — | `{ar, fr, en, total}` chunk counts |

Plus a resource: `docassist://health` — exposes the engine's health status.

## Run

```bash
# from backend/
python -m mcp_server.server                # stdio transport
mcp dev backend/mcp_server/server.py       # open the MCP Inspector
```

## Connect from Claude Desktop

Add to `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS) or the equivalent on your OS:

```json
{
  "mcpServers": {
    "docassist": {
      "command": "python",
      "args": ["-m", "mcp_server.server"],
      "cwd": "/absolute/path/to/docassist/backend"
    }
  }
}
```

Restart Claude Desktop — you'll see the 3 tools available.

## Why the tools delegate to `get_engine()`

The MCP server and the Django HTTP API share a single source of truth (`rag/my_engine.py`). Updates to the engine automatically benefit both interfaces — no duplicate logic.
