import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Badge, Card, fmtBytes, fmtDate, Icon, LangBadge, Loading, PageHead, useAsync } from "../components/ui.jsx";

export default function AdminDocs() {
  const { t, lang } = useApp();
  const [q, setQ] = useState("");
  const { data, loading, reload } = useAsync(() => api.get(`/documents/?scope=all&q=${encodeURIComponent(q)}`), [q]);
  return (
    <>
      <PageHead title={t("allDocs")} sub={`${data?.length ?? 0}`} />
      <Card>
        <input className="inp" style={{ maxWidth: 280, marginBottom: 14 }} placeholder={t("filter")} value={q} onChange={(e) => setQ(e.target.value)} dir="auto" />
        {loading && !data ? <Loading /> : (
          <div className="tbl-wrap"><table className="tbl"><thead><tr><th>{t("title")}</th><th>{t("owner")}</th><th>{t("language")}</th><th>{t("status")}</th><th>{t("size")}</th><th>{t("date")}</th><th /></tr></thead>
            <tbody>{data.map((d) => (
              <tr key={d.id}><td dir="auto"><b>{d.title}</b></td><td>{d.owner_name}</td><td><LangBadge code={d.language} /></td><td><Badge kind={d.status}>{t(d.status)}</Badge></td><td>{fmtBytes(d.size)}</td><td>{fmtDate(d.created_at, lang)}</td>
                <td className="row"><a className="btn sm" href={d.url} target="_blank" rel="noreferrer">{t("open")}</a>
                  <button className="icon-btn" style={{ color: "var(--bad)" }} onClick={async () => { if (confirm(t("confirmDelete"))) { await api.del(`/documents/${d.id}/?scope=all`); reload(); } }}><Icon n="trash" size={16} /></button></td></tr>))}</tbody></table></div>)}
      </Card>
    </>
  );
}
