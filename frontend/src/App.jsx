import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { api, token } from "./api.js";
import { DICT } from "./i18n.js";
import Layout from "./components/Layout.jsx";
import Aurora from "./components/Aurora.jsx";
import Login from "./pages/Login.jsx";
import Home from "./pages/Home.jsx";
import Documents from "./pages/Documents.jsx";
import UploadPage from "./pages/Upload.jsx";
import SearchPage from "./pages/Search.jsx";
import Chat from "./pages/Chat.jsx";
import History from "./pages/History.jsx";
import Notifications from "./pages/Notifications.jsx";
import Settings from "./pages/Settings.jsx";
import AdminOverview from "./pages/AdminOverview.jsx";
import AdminUsers from "./pages/AdminUsers.jsx";
import AdminDocs from "./pages/AdminDocs.jsx";
import AdminAudit from "./pages/AdminAudit.jsx";
import AdminModel from "./pages/AdminModel.jsx";
import AdminBroadcast from "./pages/AdminBroadcast.jsx";
import AdminAnalytics from "./pages/AdminAnalytics.jsx";
import AdminSystem from "./pages/AdminSystem.jsx";

const Ctx = createContext(null);
export const useApp = () => useContext(Ctx);

export default function App() {
  const [user, setUser] = useState(null);
  const [ready, setReady] = useState(!token());
  const [lang, setLangState] = useState(localStorage.getItem("lang") || "en");
  const [theme, setThemeState] = useState(localStorage.getItem("theme") || "dark");
  const [toast, setToast] = useState("");
  const [unread, setUnread] = useState(0);

  useEffect(() => {
    document.documentElement.dir = lang === "ar" ? "rtl" : "ltr";
    document.documentElement.lang = lang;
  }, [lang]);
  useEffect(() => { document.documentElement.dataset.theme = theme; }, [theme]);
  useEffect(() => {
    if (!token()) return;
    api.get("/auth/me/").then((u) => { setUser(u); }).catch(() => localStorage.removeItem("token")).finally(() => setReady(true));
  }, []);
  const refreshUnread = useCallback(() => token() && api.get("/notifications/").then((d) => setUnread(d.unread)).catch(() => {}), []);
  useEffect(() => { if (user && user.role !== "admin") { refreshUnread(); const id = setInterval(refreshUnread, 30000); return () => clearInterval(id); } }, [user, refreshUnread]);

  const value = useMemo(() => ({
    user, setUser, lang, theme, unread, refreshUnread,
    setLang: (l) => { localStorage.setItem("lang", l); setLangState(l); },
    setTheme: (th) => { localStorage.setItem("theme", th); setThemeState(th); },
    t: (k) => DICT[lang]?.[k] ?? DICT.en[k] ?? k,
    notify: (m) => { setToast(m); setTimeout(() => setToast(""), 2600); },
    login: (data) => { localStorage.setItem("token", data.token); setUser(data.user); },
    logout: () => { localStorage.removeItem("token"); setUser(null); },
  }), [user, lang, theme, unread, refreshUnread]);

  if (!ready) return null;
  const isAdmin = user && (user.role === "admin");
  const guard = (el) => (user ? el : <Navigate to="/login" replace />);
  const adminOnly = (el) => (isAdmin ? el : <Navigate to="/" replace />);
  const userOnly = (el) => (isAdmin ? <Navigate to="/admin" replace /> : el);

  return (
    <Ctx.Provider value={value}>
      <Aurora />
      <Routes>
        <Route path="/login" element={user ? <Navigate to={isAdmin ? "/admin" : "/"} replace /> : <Login />} />
        <Route element={guard(<Layout />)}>
          <Route path="/" element={userOnly(<Home />)} />
          <Route path="/documents" element={userOnly(<Documents />)} />
          <Route path="/upload" element={userOnly(<UploadPage />)} />
          <Route path="/search" element={userOnly(<SearchPage />)} />
          <Route path="/chat" element={userOnly(<Chat />)} />
          <Route path="/chat/:id" element={userOnly(<Chat />)} />
          <Route path="/history" element={userOnly(<History />)} />
          <Route path="/notifications" element={userOnly(<Notifications />)} />
          <Route path="/settings" element={<Settings />} />
          <Route path="/admin" element={adminOnly(<AdminOverview />)} />
          <Route path="/admin/users" element={adminOnly(<AdminUsers />)} />
          <Route path="/admin/documents" element={adminOnly(<AdminDocs />)} />
          <Route path="/admin/analytics" element={adminOnly(<AdminAnalytics />)} />
          <Route path="/admin/system" element={adminOnly(<AdminSystem />)} />
          <Route path="/admin/audit" element={adminOnly(<AdminAudit />)} />
          <Route path="/admin/model" element={adminOnly(<AdminModel />)} />
          <Route path="/admin/broadcast" element={adminOnly(<AdminBroadcast />)} />
        </Route>
        <Route path="*" element={<Navigate to={isAdmin ? "/admin" : "/"} replace />} />
      </Routes>
      {toast && <div className="toast" role="status">{toast}</div>}
    </Ctx.Provider>
  );
}
