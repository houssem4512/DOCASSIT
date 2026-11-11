import React from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Badge, Card, Empty, fmtDate, Icon, Loading, PageHead, useAsync } from "../components/ui.jsx";

export default function Notifications() {
  const { t, lang, refreshUnread } = useApp();
  const { data, loading, reload } = useAsync(() => api.get("/notifications/"));
  const after = () => { reload(); refreshUnread(); };
  if (loading && !data) return <Loading />;
  return (
    <>
      <PageHead title={t("notifications")} sub={`${data.unread} ${t("unread")}`}><button className="btn" onClick={async () => { await api.post("/notifications/read-all/"); after(); }}><Icon n="check" size={18} />{t("markAllRead")}</button></PageHead>
      <Card>{data.results.length === 0 ? <Empty title={t("noNotif")} /> : data.results.map((n) => (
        <div className="list-item" key={n.id} style={{ opacity: n.read ? 0.6 : 1 }}>
          <Badge kind={n.kind}>{n.kind}</Badge>
          <div className="grow"><div className="t" dir="auto">{n.title}</div><div className="mute" dir="auto">{n.body}</div></div>
          <span className="mute">{fmtDate(n.created_at, lang)}</span>
          {!n.read && <button className="icon-btn" onClick={async () => { await api.post(`/notifications/${n.id}/read/`); after(); }}><Icon n="check" size={16} /></button>}
          <button className="icon-btn" onClick={async () => { await api.del(`/notifications/${n.id}/`); after(); }}><Icon n="trash" size={16} /></button></div>))}</Card>
    </>
  );
}
