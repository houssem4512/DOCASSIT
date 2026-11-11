import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { LANGS } from "../i18n.js";
import { Card, Field, PageHead } from "../components/ui.jsx";

export default function Settings() {
  const { t, user, setUser, lang, setLang, theme, setTheme, notify } = useApp();
  const [f, setF] = useState({ first_name: user.first_name, last_name: user.last_name, email: user.email, password: "" });
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const save = async (e) => {
    e.preventDefault();
    try { const body = { ...f }; if (!body.password) delete body.password; setUser(await api.patch("/auth/me/", { ...body, language: lang })); notify(t("saved") + " ✓"); setF({ ...f, password: "" }); }
    catch (x) { notify(x.message); }
  };
  return (
    <>
      <PageHead title={t("settings")} sub={`@${user.username} · ${t(user.role)}`} />
      <div className="grid g2">
        <Card title={t("profile")}>
          <form onSubmit={save}>
            <Field label={t("firstName")}><input value={f.first_name} onChange={set("first_name")} dir="auto" /></Field>
            <Field label={t("lastName")}><input value={f.last_name} onChange={set("last_name")} dir="auto" /></Field>
            <Field label={t("email")}><input type="email" value={f.email} onChange={set("email")} /></Field>
            <Field label={t("password")}><input type="password" value={f.password} onChange={set("password")} minLength={6} placeholder="••••••" autoComplete="new-password" /></Field>
            <button className="btn pri">{t("save")}</button>
          </form>
        </Card>
        <Card title={t("language") + " / " + t("theme")}>
          <Field label={t("language")}><div className="seg" style={{ alignSelf: "flex-start" }}>{LANGS.map((l) => <button type="button" key={l.code} className={lang === l.code ? "on" : ""} onClick={() => setLang(l.code)}>{l.label}</button>)}</div></Field>
          <Field label={t("theme")}><div className="seg" style={{ alignSelf: "flex-start" }}>{["dark", "light"].map((m) => <button type="button" key={m} className={theme === m ? "on" : ""} onClick={() => setTheme(m)}>{t(m)}</button>)}</div></Field>
        </Card>
      </div>
    </>
  );
}
