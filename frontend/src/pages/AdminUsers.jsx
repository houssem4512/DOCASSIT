import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Badge, Card, Field, fmtDate, Icon, Loading, Modal, PageHead, useAsync } from "../components/ui.jsx";

export default function AdminUsers() {
  const { t, lang, notify, user: me } = useApp();
  const { data, loading, reload } = useAsync(() => api.get("/admin/users/"));
  const [q, setQ] = useState("");
  const [modal, setModal] = useState(false);
  const [f, setF] = useState({ username: "", email: "", first_name: "", password: "", role: "user" });
  const patch = async (u, body) => { try { await api.patch(`/admin/users/${u.id}/`, body); reload(); } catch (e) { notify(e.message); } };
  const create = async (e) => { e.preventDefault(); try { await api.post("/admin/users/", f); setModal(false); setF({ username: "", email: "", first_name: "", password: "", role: "user" }); reload(); } catch (x) { notify(x.message); } };
  if (loading && !data) return <Loading />;
  const rows = data.filter((u) => (u.username + u.email).toLowerCase().includes(q.toLowerCase()));
  return (
    <>
      <PageHead title={t("users")} sub={`${data.length}`}><button className="btn pri" onClick={() => setModal(true)}><Icon n="plus" size={18} />{t("newUser")}</button></PageHead>
      <Card>
        <input className="inp" style={{ maxWidth: 280, marginBottom: 14 }} placeholder={t("filter")} value={q} onChange={(e) => setQ(e.target.value)} />
        <div className="tbl-wrap"><table className="tbl"><thead><tr><th>{t("username")}</th><th>{t("email")}</th><th>{t("role")}</th><th>{t("docsCount")}</th><th>{t("active")}</th><th>{t("date")}</th><th /></tr></thead>
          <tbody>{rows.map((u) => (
            <tr key={u.id}><td><b>{u.username}</b><div className="mute">{u.first_name}</div></td><td>{u.email || "—"}</td>
              <td><select className="inp" style={{ width: 120, padding: "6px 10px" }} value={u.role} disabled={u.id === me.id} onChange={(e) => patch(u, { role: e.target.value })}><option value="user">{t("user")}</option><option value="admin">{t("admin")}</option></select></td>
              <td>{u.documents_count}</td>
              <td><button className="btn sm" disabled={u.id === me.id} onClick={() => patch(u, { is_active: !u.is_active })}><Badge kind={u.is_active ? "success" : "error"}>{u.is_active ? t("active") : "—"}</Badge></button></td>
              <td>{fmtDate(u.date_joined, lang)}</td>
              <td>{u.id !== me.id && <button className="icon-btn" style={{ color: "var(--bad)" }} onClick={async () => { if (confirm(t("confirmDelete"))) { await api.del(`/admin/users/${u.id}/`); reload(); } }}><Icon n="trash" size={16} /></button>}</td></tr>))}</tbody></table></div>
      </Card>
      {modal && <Modal title={t("newUser")} onClose={() => setModal(false)}>
        <form onSubmit={create}>
          <Field label={t("username")}><input required value={f.username} onChange={(e) => setF({ ...f, username: e.target.value })} /></Field>
          <Field label={t("firstName")}><input value={f.first_name} onChange={(e) => setF({ ...f, first_name: e.target.value })} dir="auto" /></Field>
          <Field label={t("email")}><input type="email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} /></Field>
          <Field label={t("password")}><input type="password" required minLength={6} value={f.password} onChange={(e) => setF({ ...f, password: e.target.value })} /></Field>
          <Field label={t("role")}><select value={f.role} onChange={(e) => setF({ ...f, role: e.target.value })}><option value="user">{t("user")}</option><option value="admin">{t("admin")}</option></select></Field>
          <div className="row" style={{ justifyContent: "flex-end" }}><button type="button" className="btn" onClick={() => setModal(false)}>{t("cancel")}</button><button className="btn pri">{t("create")}</button></div>
        </form></Modal>}
    </>
  );
}
