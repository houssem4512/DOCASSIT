import React from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Donut } from "../components/charts.jsx";
import { Badge, Card, fmtBytes, fmtDate, Icon, Loading, PageHead, Stat, useAsync } from "../components/ui.jsx";

const dur = (s) => { const d = Math.floor(s / 86400), h = Math.floor((s % 86400) / 3600), m = Math.floor((s % 3600) / 60); return `${d ? d + "d " : ""}${h}h ${m}m`; };

export default function AdminSystem() {
  const { t, lang, notify } = useApp();
  const sys = useAsync(() => api.get("/admin/system/"));
  const feed = useAsync(() => api.get("/admin/feed/"));
  if (!sys.data || !feed.data) return <Loading />;
  const s = sys.data, failed = feed.data.failed_documents;
  const pct = Math.round((s.disk.used / s.disk.total) * 100);
  const rows = [["Python", s.python], ["Django", s.django], ["OS", s.os], [t("engine"), s.engine], ["DEBUG", String(s.debug)], [t("limits"), `${s.max_upload_mb} MB · ${s.extensions.join(" ")}`], ["Server time", fmtDate(s.server_time, lang)]];
  const colors = { ready: "#16a37a", processing: "#f59e0b", pending: "#3b82f6", failed: "#e5484d" };
  return (
    <>
      <PageHead title={t("system")} sub={t("adminConsole")}><button className="btn" onClick={() => { sys.reload(); feed.reload(); }}><Icon n="refresh" size={18} /></button></PageHead>
      <div className="grid g4" style={{ marginBottom: 18 }}>
        <Stat icon="bolt" value={dur(s.uptime)} label={t("uptime")} /><Stat icon="db" value={fmtBytes(s.db_size)} label={t("dbSize")} />
        <Stat icon="file" value={fmtBytes(s.media_size)} label={t("mediaSize")} /><Stat icon="cpu" value={s.rag.connected ? t("connected") : t("notConnected")} label="RAG" />
      </div>
      <div className="grid g2" style={{ marginBottom: 18 }}>
        <Card title={t("diskUsage")}>
          <div className="row" style={{ justifyContent: "space-between" }}><b>{fmtBytes(s.disk.used)} / {fmtBytes(s.disk.total)}</b><Badge kind={pct > 85 ? "error" : "success"}>{pct}%</Badge></div>
          <div className="meter" style={{ margin: "10px 0" }}><div style={{ width: pct + "%", background: pct > 85 ? "var(--bad)" : undefined }} /></div>
          <div className="mute">{fmtBytes(s.disk.free)} free</div>
        </Card>
        <Card title={t("docStatus")}><Donut size={120} data={Object.entries(s.status).map(([k, v]) => ({ label: t(k), value: v, color: colors[k] }))} /></Card>
      </div>
      <div className="grid g2">
        <Card title={t("serverInfo")}>{rows.map(([k, v]) => <div className="list-item" key={k}><span className="mute" style={{ width: 120 }}>{k}</span><span className="grow" style={{ wordBreak: "break-all" }}>{v}</span></div>)}
          <Link to="/admin/model" className="btn sm" style={{ marginTop: 12 }}><Icon n="cpu" size={16} />{t("model")}</Link></Card>
        <Card title={t("failedDocs")} right={failed.length > 0 && <button className="btn sm pri" onClick={async () => { const r = await api.post("/admin/system/reindex-failed/"); notify(`${r.count} ${t("reindexed")}`); feed.reload(); sys.reload(); }}>{t("reindexFailed")}</button>}>
          {failed.length === 0 ? <Badge kind="success">{t("noFailed")}</Badge> : failed.map((d) => (
            <div className="list-item" key={d.id}><Badge kind="error">{t("failed")}</Badge><div className="grow"><div className="t" dir="auto">{d.title}</div><div className="mute">{d.owner__username} · {d.error}</div></div></div>))}
        </Card>
      </div>
    </>
  );
}
