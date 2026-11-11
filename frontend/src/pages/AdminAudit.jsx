import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Badge, Card, fmtDate, Loading, PageHead, useAsync } from "../components/ui.jsx";

export default function AdminAudit() {
  const { t, lang } = useApp();
  const { data, loading } = useAsync(() => api.get("/admin/audit/"));
  const [q, setQ] = useState("");
  if (loading && !data) return <Loading />;
  const rows = data.filter((r) => (r.user + r.action + r.detail).toLowerCase().includes(q.toLowerCase()));
  return (
    <>
      <PageHead title={t("audit")} sub={`${rows.length}`} />
      <Card>
        <input className="inp" style={{ maxWidth: 280, marginBottom: 14 }} placeholder={t("filter")} value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="tbl-wrap"><table className="tbl"><thead><tr><th>{t("date")}</th><th>{t("user")}</th><th>{t("action")}</th><th>{t("detail")}</th><th>{t("ip")}</th></tr></thead>
          <tbody>{rows.map((r) => <tr key={r.id}><td>{fmtDate(r.created_at, lang)}</td><td>{r.user}</td><td><Badge kind="info">{r.action}</Badge></td><td dir="auto">{r.detail}</td><td>{r.ip}</td></tr>)}</tbody></table></div>
      </Card>
    </>
  );
}
