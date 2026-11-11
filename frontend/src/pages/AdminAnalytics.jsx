import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Columns, Donut, HBars, LineChart } from "../components/charts.jsx";
import { Card, fmtBytes, Loading, PageHead, useAsync } from "../components/ui.jsx";

export default function AdminAnalytics() {
  const { t } = useApp();
  const [days, setDays] = useState(30);
  const { data: d, loading } = useAsync(() => api.get(`/admin/analytics/?days=${days}`), [days]);
  if (!d) return <Loading />;
  const ser = d.series, col = (k) => ser.map((x) => x[k]);
  const k = d.kpi;
  const wd = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"].map(t);
  const kp = [[t("avgDocSize"), fmtBytes(k.avg_doc_size)], [t("qPerUser"), k.questions_per_user], [t("dPerUser"), k.docs_per_user], [t("successRate"), k.success_rate + "%"], [t("sourcedRate"), k.sourced_rate + "%"]];
  return (
    <>
      <PageHead title={t("analytics")} sub={t("adminConsole")}>
        <div className="seg">{[[7, "days7"], [30, "days30"], [90, "days90"]].map(([n, key]) => <button key={n} className={days === n ? "on" : ""} onClick={() => setDays(n)}>{t(key)}</button>)}</div>
      </PageHead>
      <div className="grid" style={{ gridTemplateColumns: "repeat(5,1fr)", marginBottom: 18, opacity: loading ? 0.6 : 1 }}>
        {kp.map(([l, v]) => <div className="card kpi" key={l}><div className="lbl">{l}</div><b>{v}</b></div>)}
      </div>
      <Card title={t("dailyActivity")} className="" >
        <LineChart height={260} labels={ser.map((x) => x.date)} series={[
          { name: t("uploads"), color: "#7c5cff", values: col("uploads") },
          { name: t("questionsTotal"), color: "#ff4fa3", values: col("questions") },
          { name: t("signups"), color: "#22d3ee", values: col("signups") },
          { name: t("activeDaily"), color: "#16a37a", values: col("active") }]} />
      </Card>
      <div className="grid g2" style={{ margin: "18px 0" }}>
        <Card title={t("peakHours")}><Columns values={d.hourly} labels={Array.from({ length: 24 }, (_, i) => i + "h")} /></Card>
        <Card title={t("byWeekday")}><Columns values={d.weekday} labels={wd} /></Card>
      </div>
      <div className="grid g3">
        <Card title={t("fileTypes")}><Donut size={120} center={Object.values(d.file_types).reduce((a, b) => a + b, 0)} data={Object.entries(d.file_types).map(([l, v]) => ({ label: l.toUpperCase(), value: v }))} /></Card>
        <Card title={t("questionLangs")}><Donut size={120} data={[{ label: "العربية", value: d.question_languages.ar, color: "#7c5cff" }, { label: "Français", value: d.question_languages.fr, color: "#ff4fa3" }, { label: "English", value: d.question_languages.en, color: "#22d3ee" }]} /></Card>
        <Card title={t("storageByUser")}><HBars rows={d.storage_by_user.map((u) => ({ label: u.username, value: u.s || 0, text: fmtBytes(u.s || 0) }))} /></Card>
      </div>
    </>
  );
}
