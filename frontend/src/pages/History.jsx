import React from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Card, Empty, fmtDate, Icon, Loading, PageHead, useAsync } from "../components/ui.jsx";

export default function History() {
  const { t, lang } = useApp();
  const { data, loading, reload } = useAsync(() => api.get("/conversations/"));
  if (loading && !data) return <Loading />;
  return (
    <>
      <PageHead title={t("history")}><Link to="/chat" className="btn pri"><Icon n="plus" size={18} />{t("newChat")}</Link></PageHead>
      <Card>{!data?.length ? <Empty title={t("noChats")} /> : data.map((c) => (
        <div className="list-item" key={c.id}><div className="file-ic"><Icon n="chat" /></div>
          <Link to={"/chat/" + c.id} className="grow"><div className="t" dir="auto">{c.title}</div><div className="mute">{c.message_count} · {fmtDate(c.updated_at, lang)}</div></Link>
          <button className="icon-btn" style={{ color: "var(--bad)" }} title={t("deleteChat")} onClick={async () => { if (confirm(t("confirmDelete"))) { await api.del(`/conversations/${c.id}/`); reload(); } }}><Icon n="trash" size={16} /></button></div>))}</Card>
    </>
  );
}
