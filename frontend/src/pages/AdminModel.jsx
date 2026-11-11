import React, { useEffect, useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Badge, Card, Field, Loading, PageHead, useAsync } from "../components/ui.jsx";

const SNIPPET = `# backend/rag/my_engine.py
from rag.engine import BaseRAGEngine

class MyRAGEngine(BaseRAGEngine):
    def health(self):  return {"connected": True, "model": "...", "embedding_model": "...", "vector_store": "...", "detail": "ok"}
    def ingest(self, document):   # parse + chunk + embed document.file.path
        return {"status": "ready", "pages": 12, "language": "fr", "error": None}
    def delete(self, document):   ...
    def search(self, query, user, document_ids=None, language=None, top_k=5):
        return [{"document_id": 1, "title": "...", "page": 3, "snippet": "...", "score": 0.82}]
    def answer(self, question, user, document_ids=None, history=None, language=None):
        return {"answer": "...", "language": "ar", "sources": [...]}

# then run:  RAG_ENGINE=rag.my_engine.MyRAGEngine python manage.py runserver`;

export default function AdminModel() {
  const { t, notify } = useApp();
  const health = useAsync(() => api.get("/admin/rag/health/"));
  const [cfg, setCfg] = useState(null);
  const [query, setQuery] = useState("");
  const [out, setOut] = useState(null);
  useEffect(() => { api.get("/admin/rag/settings/").then(setCfg); }, []);
  if (!cfg || health.loading) return <Loading />;
  const h = health.data;
  const set = (k, num) => (e) => setCfg({ ...cfg, [k]: num ? Number(e.target.value) : e.target.value });
  return (
    <>
      <PageHead title={t("model")} sub={t("modelStatus")}><Badge kind={h.connected ? "success" : "warning"}>{h.connected ? t("connected") : t("notConnected")}</Badge></PageHead>
      <div className="grid g2" style={{ marginBottom: 18 }}>
        <Card title={t("config")}>
          <form onSubmit={async (e) => { e.preventDefault(); await api.put("/admin/rag/settings/", cfg); notify(t("saved") + " ✓"); }}>
            <Field label="LLM"><input value={cfg.llm_model} onChange={set("llm_model")} /></Field>
            <Field label="Embeddings"><input value={cfg.embedding_model} onChange={set("embedding_model")} /></Field>
            <Field label="Vector store"><select value={cfg.vector_store} onChange={set("vector_store")}>{["faiss", "chroma", "qdrant", "pgvector"].map((v) => <option key={v}>{v}</option>)}</select></Field>
            <div className="grid g3"><Field label="Chunk size"><input type="number" value={cfg.chunk_size} onChange={set("chunk_size", 1)} /></Field>
              <Field label="Overlap"><input type="number" value={cfg.chunk_overlap} onChange={set("chunk_overlap", 1)} /></Field>
              <Field label="Top-k"><input type="number" value={cfg.top_k} onChange={set("top_k", 1)} /></Field></div>
            <button className="btn pri">{t("save")}</button>
          </form>
          <p className="mute" style={{ marginTop: 12 }}>These values are stored in the database; read them in your engine with <code>AppSetting.objects.get(key="rag").value</code>.</p>
        </Card>
        <Card title={t("testConsole")}>
          <Field label={t("askPlaceholder")}><textarea rows={3} dir="auto" value={query} onChange={(e) => setQuery(e.target.value)} /></Field>
          <button className="btn pri" disabled={!query.trim()} onClick={async () => setOut(await api.post("/admin/rag/test/", { query }))}>{t("runTest")}</button>
          {out && <pre className="code" style={{ marginTop: 14, whiteSpace: "pre-wrap" }}>{JSON.stringify(out, null, 2)}</pre>}
          <p className="mute" style={{ marginTop: 12 }}>{h.detail}</p>
        </Card>
      </div>
      <Card title={t("integrate")}><pre className="code">{SNIPPET}</pre></Card>
    </>
  );
}
