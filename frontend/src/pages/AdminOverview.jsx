import React from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Columns, Delta, Donut, HBars, LineChart, Spark } from "../components/charts.jsx";
import { Badge, Card, fmtBytes, fmtDate, Icon, Loading, PageHead, useAsync } from "../components/ui.jsx";

function Kpi({ label, value, cmp, spark, color, t }) {
  return (
    <div className="card kpi"><div className="lbl">{label}</div><b>{value}</b>
      <div><Delta cur={cmp.week} prev={cmp.prev} /> <span className="mute">{t("weekVs")}</span></div>
      <Spark values={spark} color={color} /></div>
  );
}

export default function AdminOverview() {
  const { t, lang } = useApp();
  const s = useAsync(() => api.get("/admin/stats/"));
  const f = useAsync(() => api.get("/admin/feed/"));
  const a = useAsync(() => api.get("/admin/analytics/?days=14"));
  const h = useAsync(() => api.get("/admin/rag/health/"));
  if (!s.data || !f.data || !a.data) return <Loading />;
  const st = s.data, fd = f.data, an = a.data, ser = an.series;
  const col = (k) => ser.map((x) => x[k]);
  return (
    <>
      <PageHead title={t("overview")} sub={t("adminConsole")}>
        {h.data && <Badge kind={h.data.connected ? "success" : "warning"}>RAG: {h.data.connected ? t("connected") : t("notConnected")}</Badge>}
        <Link className="btn sm" to="/admin/analytics"><Icon n="bolt" size={16} />{t("analytics")}</Link>
      </PageHead>

      {fd.failed_documents.length > 0 && (
        <div className="card alert" style={{ marginBottom: 18 }}><div className="row" style={{ justifyContent: "space-between" }}>
          <b>⚠ {fd.failed_documents.length} {t("failedDocs").toLowerCase()}</b><Link to="/admin/system" className="btn sm">{t("system")}</Link></div></div>)}

      <div className="grid g4" style={{ marginBottom: 18 }}>
        <Kpi t={t} label={t("usersTotal")} value={st.users} cmp={fd.users} spark={col("signups")} color="#7c5cff" />
        <Kpi t={t} label={t("docsTotal")} value={st.documents} cmp={fd.documents} spark={col("uploads")} color="#ff4fa3" />
        <Kpi t={t} label={t("questionsTotal")} value={st.questions} cmp={fd.questions} spark={col("questions")} color="#22d3ee" />
        <Kpi t={t} label={t("activeDaily")} value={st.active_users + "/" + st.users} cmp={fd.logins} spark={col("active")} color="#16a37a" />
      </div>

      <div className="grid g21" style={{ marginBottom: 18 }}>
        <Card title={t("dailyActivity")}>
          <LineChart labels={ser.map((x) => x.date)} series={[
            { name: t("uploads"), color: "#7c5cff", values: col("uploads") },
            { name: t("questionsTotal"), color: "#ff4fa3", values: col("questions") },
            { name: t("signups"), color: "#22d3ee", values: col("signups") }]} />
        </Card>
        <div className="grid">
          <Card title={t("byLanguage")}><Donut size={120} center={st.documents} data={[{ label: "العربية", value: st.by_language.ar, color: "#7c5cff" }, { label: "Français", value: st.by_language.fr, color: "#ff4fa3" }, { label: "English", value: st.by_language.en, color: "#22d3ee" }]} /></Card>
          <Card title={t("docStatus")}><HBars rows={Object.entries(st.by_status).map(([k, v]) => ({ label: t(k), value: v }))} />
            <div className="mute">{t("storage")}: <b style={{ color: "var(--text)" }}>{fmtBytes(st.storage)}</b></div></Card>
        </div>
      </div>

      <div className="grid g3" style={{ marginBottom: 18 }}>
        <Card title={t("liveFeed")}>{fd.events.length === 0 ? <span className="mute">—</span> : fd.events.slice(0, 7).map((e) => (
          <div className="feed-i" key={e.id}><span className="pulse-dot" /><div className="grow" style={{ minWidth: 0 }}><b>{e.user}</b> <Badge kind="info">{e.action}</Badge><div className="mute" dir="auto" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>{e.detail} · {fmtDate(e.created_at, lang)}</div></div></div>))}
          <Link to="/admin/audit" className="mute">{t("audit")} →</Link></Card>
        <Card title={t("recentSignups")}>{fd.recent_users.map((u) => (
          <div className="list-item" key={u.id}><div className="avatar" style={{ width: 32, height: 32, fontSize: 13, cursor: "default" }}>{u.username[0].toUpperCase()}</div><div className="grow"><div className="t">{u.username}</div><div className="mute">{fmtDate(u.date_joined, lang)}</div></div><Badge kind={u.role === "admin" ? "warning" : "info"}>{t(u.role)}</Badge></div>))}</Card>
        <Card title={t("topUsers")}><HBars rows={st.top_users.map((u) => ({ label: u.username, value: u.n }))} />
          <h3 style={{ margin: "18px 0 8px" }}>{t("peakHours")}</h3><Columns values={an.hourly} labels={Array.from({ length: 24 }, (_, i) => i + "h")} /></Card>
      </div>
    </>
  );
}
