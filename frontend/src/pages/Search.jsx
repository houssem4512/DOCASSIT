import React, { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Card, Empty, Icon, Loading, PageHead } from "../components/ui.jsx";

export default function SearchPage() {
  const { t } = useApp();
  const [sp, setSp] = useSearchParams();
  const nav = useNavigate();
  const [q, setQ] = useState(sp.get("q") || "");
  const [language, setLanguage] = useState("");
  const [res, setRes] = useState(null);
  const [busy, setBusy] = useState(false);
  const run = async (query = q) => {
    if (!query.trim()) return setRes(null);
    setBusy(true);
    try { setRes(await api.get(`/search/?q=${encodeURIComponent(query)}&language=${language}`)); } finally { setBusy(false); }
  };
  useEffect(() => { setQ(sp.get("q") || ""); run(sp.get("q") || ""); }, [sp.get("q")]); // eslint-disable-line
  const ask = async (r) => { const c = await api.post("/conversations/", { title: q, document_ids: [r.document_id] }); nav("/chat/" + c.id); };
  return (
    <>
      <PageHead title={t("search")} sub={t("typeToSearch")} />
      <form className="row" style={{ marginBottom: 18 }} onSubmit={(e) => { e.preventDefault(); setSp(q ? { q } : {}); run(); }}>
        <input className="inp" style={{ flex: 1, minWidth: 220 }} value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("searchPlaceholder")} dir="auto" autoFocus />
        <select className="inp" style={{ width: 150 }} value={language} onChange={(e) => setLanguage(e.target.value)}><option value="">{t("all")}</option><option value="ar">العربية</option><option value="fr">Français</option><option value="en">English</option></select>
        <button className="btn pri"><Icon n="search" size={18} />{t("search")}</button>
      </form>
      {busy ? <Loading /> : res === null ? <Card><Empty title={t("search")} hint={t("typeToSearch")} /></Card> : res.length === 0 ? <Card><Empty title={t("noResults")} /></Card> : (
        <div className="grid">{res.map((r, i) => (
          <Card key={i}><div className="row" style={{ justifyContent: "space-between" }}><b dir="auto">{r.title} <span className="mute">· p.{r.page}</span></b><span className="mute">{(r.score * 100).toFixed(0)}%</span></div>
            <p dir="auto" style={{ margin: "8px 0 12px", lineHeight: 1.7 }}>{r.snippet}</p>
            <button className="btn sm pri" onClick={() => ask(r)}>{t("ask")}</button></Card>))}</div>)}
    </>
  );
}
