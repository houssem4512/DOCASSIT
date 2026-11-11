import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Card, Field, PageHead } from "../components/ui.jsx";

export default function AdminBroadcast() {
  const { t, notify } = useApp();
  const [f, setF] = useState({ title: "", body: "", kind: "info" });
  const send = async (e) => { e.preventDefault(); const r = await api.post("/admin/notifications/broadcast/", f); notify(`${t("sent")} ${r.sent}`); setF({ title: "", body: "", kind: "info" }); };
  return (
    <>
      <PageHead title={t("broadcast")} sub={t("sendToAll")} />
      <div style={{ maxWidth: 620 }}><Card>
        <form onSubmit={send}>
          <Field label={t("title")}><input required value={f.title} onChange={(e) => setF({ ...f, title: e.target.value })} dir="auto" /></Field>
          <Field label={t("message")}><textarea rows={4} value={f.body} onChange={(e) => setF({ ...f, body: e.target.value })} dir="auto" /></Field>
          <Field label={t("kind")}><select value={f.kind} onChange={(e) => setF({ ...f, kind: e.target.value })}>{["info", "success", "warning", "error"].map((k) => <option key={k}>{k}</option>)}</select></Field>
          <button className="btn pri">{t("sendToAll")}</button>
        </form></Card></div>
    </>
  );
}
