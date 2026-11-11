import React, { useState } from "react";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import Cover from "../components/Cover.jsx";
import { LangSwitch, ThemeToggle } from "../components/Layout.jsx";

export default function Login() {
  const { t, login, lang } = useApp();
  const [mode, setMode] = useState("in");
  const [f, setF] = useState({ username: "", password: "", email: "", first_name: "" });
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const submit = async (e) => {
    e.preventDefault(); setErr(""); setBusy(true);
    try {
      const data = mode === "in" ? await api.post("/auth/login/", { username: f.username, password: f.password }) : await api.post("/auth/register/", { ...f, language: lang });
      login(data);
    } catch (x) { setErr(x.message); } finally { setBusy(false); }
  };
  return (
    <div className="auth">
      <div className="auth-top"><LangSwitch /><ThemeToggle /></div>
      <div className="auth-l">
        <div className="brand" style={{ padding: 0 }}><div className="logo">L</div><div><b style={{ fontSize: 24 }}>Lexia</b></div></div>
        <p className="mute" style={{ margin: "8px 0 0", maxWidth: 380 }}>{t("heroSub")}</p>
        <div className="auth-tabs">
          <button className={mode === "in" ? "on" : ""} onClick={() => setMode("in")}>{t("signin")}</button>
          <button className={mode === "up" ? "on" : ""} onClick={() => setMode("up")}>{t("signup")}</button>
        </div>
        <form onSubmit={submit}>
          {mode === "up" && <><div className="field"><input placeholder={t("firstName")} value={f.first_name} onChange={set("first_name")} dir="auto" /></div>
            <div className="field"><input type="email" placeholder={t("email")} value={f.email} onChange={set("email")} /></div></>}
          <div className="field"><input placeholder={t("username")} value={f.username} onChange={set("username")} required autoFocus autoComplete="username" /></div>
          <div className="field"><input type="password" placeholder={t("password")} value={f.password} onChange={set("password")} required minLength={mode === "up" ? 6 : 1} autoComplete={mode === "in" ? "current-password" : "new-password"} /></div>
          {err && <p className="err">{err}</p>}
          <button className="btn pri" style={{ width: "100%", padding: 13 }} disabled={busy}>{mode === "in" ? t("signin") : t("signup")}</button>
        </form>
        <p className="mute" style={{ marginTop: 16 }}>{mode === "in" ? t("noAccount") : t("haveAccount")} <a href="#" style={{ color: "var(--a1)", fontWeight: 700 }} onClick={(e) => { e.preventDefault(); setMode(mode === "in" ? "up" : "in"); }}>{mode === "in" ? t("signup") : t("signin")}</a></p>
        <p className="mute" dir="ltr">{t("demoHint")}</p>
      </div>
      <div className="auth-r"><Cover /></div>
    </div>
  );
}
