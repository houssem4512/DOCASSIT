import React, { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Badge, Card, Empty, fmtBytes, fmtDate, Icon, LangBadge, Loading, PageHead, useAsync } from "../components/ui.jsx";

export default function Documents() {
  const { t, lang, notify } = useApp();
  const nav = useNavigate();
  const [q, setQ] = useState(""); const [language, setLanguage] = useState(""); const [status, setStatus] = useState("");
  const { data, loading, reload } = useAsync(() => api.get(`/documents/?q=${encodeURIComponent(q)}&language=${language}&status=${status}`), [q, language, status]);
  const del = async (d) => { if (confirm(t("confirmDelete"))) { await api.del(`/documents/${d.id}/`); notify(t("delete") + " ✓"); reload(); } };
  const reindex = async (d) => { await api.post(`/documents/${d.id}/reindex/`); reload(); };
  const ask = async (d) => { const c = await api.post("/conversations/", { title: d.title, document_ids: [d.id] }); nav("/chat/" + c.id); };
  return (
    <>
      <PageHead title={t("documents")} sub={`${data?.length ?? 0} ${t("docsCount").toLowerCase()}`}><Link to="/upload" className="btn pri"><Icon n="upload" size={18} />{t("upload")}</Link></PageHead>
      <Card>
        <div className="row" style={{ marginBottom: 14 }}>
          <input className="inp" style={{ maxWidth: 260 }} placeholder={t("filter")} value={q} onChange={(e) => setQ(e.target.value)} dir="auto" />
          <select className="inp" style={{ maxWidth: 160 }} value={language} onChange={(e) => setLanguage(e.target.value)}><option value="">{t("language")}: {t("all")}</option><option value="ar">العربية</option><option value="fr">Français</option><option value="en">English</option></select>
          <select className="inp" style={{ maxWidth: 160 }} value={status} onChange={(e) => setStatus(e.target.value)}><option value="">{t("status")}: {t("all")}</option>{["ready", "processing", "pending", "failed"].map((s) => <option key={s} value={s}>{t(s)}</option>)}</select>
        </div>
        {loading && !data ? <Loading /> : !data?.length ? <Empty title={t("noDocs")} hint={t("noDocsHint")}><Link to="/upload" className="btn pri">{t("uploadDoc")}</Link></Empty> : (
          <div className="tbl-wrap"><table className="tbl"><thead><tr><th>{t("title")}</th><th>{t("language")}</th><th>{t("status")}</th><th>{t("pages")}</th><th>{t("size")}</th><th>{t("date")}</th><th>{t("actions")}</th></tr></thead>
            <tbody>{data.map((d) => (
              <tr key={d.id}><td><div className="row"><div className="file-ic"><Icon n="pdf" /></div><b dir="auto">{d.title}</b></div></td>
                <td><LangBadge code={d.language} /></td><td><Badge kind={d.status}>{t(d.status)}</Badge></td><td>{d.pages || "—"}</td><td>{fmtBytes(d.size)}</td><td>{fmtDate(d.created_at, lang)}</td>
                <td><div className="row" style={{ gap: 6 }}>
                  <button className="btn sm pri" onClick={() => ask(d)} disabled={d.status !== "ready"}>{t("ask")}</button>
                  <a className="btn sm" href={d.url} target="_blank" rel="noreferrer">{t("open")}</a>
                  <button className="icon-btn" style={{ width: 32, height: 32 }} onClick={() => reindex(d)} title={t("reindex")}><Icon n="refresh" size={16} /></button>
                  <button className="icon-btn" style={{ width: 32, height: 32, color: "var(--bad)" }} onClick={() => del(d)} title={t("delete")}><Icon n="trash" size={16} /></button></div></td></tr>))}</tbody></table></div>)}
      </Card>
    </>
  );
}
