import React, { useState } from "react";
import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useApp } from "../App.jsx";
import { LANGS } from "../i18n.js";
import { Icon } from "./ui.jsx";

export function LangSwitch() {
  const { lang, setLang } = useApp();
  return <div className="seg" role="group" aria-label="Language">{LANGS.map((l) => <button key={l.code} className={lang === l.code ? "on" : ""} onClick={() => setLang(l.code)} title={l.label}>{l.short}</button>)}</div>;
}
export function ThemeToggle() {
  const { theme, setTheme } = useApp();
  return <button className="icon-btn" onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme" title="Dark / Light"><Icon n={theme === "dark" ? "sun" : "moon"} /></button>;
}

const USER_NAV = [["/", "home", "home"], ["/documents", "documents", "file"], ["/upload", "upload", "upload"], ["/search", "search", "search"], ["/chat", "chat", "chat"], ["/history", "history", "clock"], ["/notifications", "notifications", "bell"], ["/settings", "settings", "gear"]];
const ADMIN_NAV = [["/admin", "overview", "grid"], ["/admin/analytics", "analytics", "bolt"], ["/admin/users", "users", "users"], ["/admin/documents", "allDocs", "db"], ["/admin/model", "model", "cpu"], ["/admin/system", "system", "shield"], ["/admin/audit", "audit", "clock"], ["/admin/broadcast", "broadcast", "megaphone"], ["/settings", "settings", "gear"]];

export default function Layout() {
  const { t, user, logout, unread } = useApp();
  const nav = useNavigate();
  const [menu, setMenu] = useState(false);
  const [q, setQ] = useState("");
  const isAdmin = user.role === "admin";
  const items = isAdmin ? ADMIN_NAV : USER_NAV;
  const link = ([to, key, ic]) => (
    <NavLink key={to} to={to} end={to === "/" || to === "/admin"} className={({ isActive }) => (isActive ? "on" : "")}>
      <Icon n={ic} />{t(key)}{key === "notifications" && unread > 0 && <span className="badge-n">{unread}</span>}
    </NavLink>
  );
  return (
    <div className="shell">
      <aside className="side">
        <div className="brand"><div className="logo">L</div><div><b>Lexia</b>{isAdmin ? <span className="admin-tag">{t("adminConsole")}</span> : <small>{t("appTagline")}</small>}</div></div>
        <nav className="nav">{items.map(link)}</nav>
        <div className="side-foot"><b style={{ color: "var(--text)" }}>{user.first_name || user.username}</b><br />{isAdmin ? t("admin") : t("user")} · AR / FR / EN</div>
      </aside>
      <div className="main">
        <header className="top">
          {!isAdmin && (
            <form className="search-box" onSubmit={(e) => { e.preventDefault(); q && nav("/search?q=" + encodeURIComponent(q)); }}>
              <Icon n="search" size={18} /><input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t("searchPlaceholder")} dir="auto" />
            </form>)}
          <div className="grow" />
          <LangSwitch /><ThemeToggle />
          {!isAdmin && <button className="icon-btn" onClick={() => nav("/notifications")} aria-label={t("notifications")}><Icon n="bell" />{unread > 0 && <span className="dot" />}</button>}
          <div style={{ position: "relative" }}>
            <button className="avatar" onClick={() => setMenu(!menu)} aria-label="Account">{(user.first_name || user.username)[0].toUpperCase()}</button>
            {menu && <div className="pop" onClick={() => setMenu(false)}>
              <NavLink to="/settings">{t("settings")}</NavLink>
              <button onClick={() => { logout(); nav("/login"); }}>{t("logout")}</button>
            </div>}
          </div>
        </header>
        <nav className="mobnav">{items.map(([to, key]) => <NavLink key={to} to={to} end className={({ isActive }) => (isActive ? "on" : "")}>{t(key)}</NavLink>)}</nav>
        <main className="content"><Outlet /></main>
      </div>
    </div>
  );
}
