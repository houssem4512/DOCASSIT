import React, { useCallback, useEffect, useState } from "react";
import { useApp } from "../App.jsx";

const P = {
  home: "M3 11l9-8 9 8M5 10v10h14V10", file: "M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8zM14 3v5h5M9 13h6M9 17h6",
  upload: "M12 16V4M7 9l5-5 5 5M4 20h16", search: "M11 18a7 7 0 100-14 7 7 0 000 14zM21 21l-4.3-4.3", chat: "M21 12a8 8 0 01-11.6 7.1L4 20l1-4.6A8 8 0 1121 12z",
  clock: "M12 21a9 9 0 100-18 9 9 0 000 18zM12 7v5l3 2", bell: "M18 16v-5a6 6 0 10-12 0v5l-2 2h16zM10 21h4", gear: "M12 15a3 3 0 100-6 3 3 0 000 6zM19 12a7 7 0 00-.1-1.2l2-1.5-2-3.4-2.3.9a7 7 0 00-2-1.2L14 3h-4l-.6 2.6a7 7 0 00-2 1.2l-2.3-.9-2 3.4 2 1.5A7 7 0 005 12a7 7 0 00.1 1.2l-2 1.5 2 3.4 2.3-.9a7 7 0 002 1.2L10 21h4l.6-2.6a7 7 0 002-1.2l2.3.9 2-3.4-2-1.5c.1-.4.1-.8.1-1.2z",
  grid: "M4 4h7v7H4zM13 4h7v7h-7zM4 13h7v7H4zM13 13h7v7h-7z", users: "M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM22 21v-2a4 4 0 00-3-3.9M16 3.1a4 4 0 010 7.8",
  shield: "M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z", cpu: "M7 7h10v10H7zM9 3v4M15 3v4M9 17v4M15 17v4M3 9h4M3 15h4M17 9h4M17 15h4", megaphone: "M3 11v3a1 1 0 001 1h3l8 4V6L7 10H4a1 1 0 00-1 1zM19 8a5 5 0 010 8",
  sun: "M12 17a5 5 0 100-10 5 5 0 000 10zM12 1v2M12 21v2M4.2 4.2l1.4 1.4M18.4 18.4l1.4 1.4M1 12h2M21 12h2M4.2 19.8l1.4-1.4M18.4 5.6l1.4-1.4", moon: "M21 13A9 9 0 1111 3a7 7 0 0010 10z",
  trash: "M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3", plus: "M12 5v14M5 12h14", send: "M22 2L11 13M22 2l-7 20-4-9-9-4z", check: "M5 13l4 4L19 7", logout: "M9 21H5V3h4M16 17l5-5-5-5M21 12H9",
  refresh: "M20 11A8 8 0 006 6L4 8M4 4v4h4M4 13a8 8 0 0014 5l2-2M20 20v-4h-4", pdf: "M14 3H7a2 2 0 00-2 2v14a2 2 0 002 2h10a2 2 0 002-2V8zM14 3v5h5", db: "M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zM4 6v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3",
  bolt: "M13 2L4 14h7l-1 8 9-12h-7z", paperclip: "M21 11l-9 9a5 5 0 01-7-7l9-9a3 3 0 014 4l-9 9a1 1 0 01-2-2l8-8",
};
export const Icon = ({ n, size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d={P[n]} /></svg>
);

export const fmtBytes = (b = 0) => (b < 1024 ? b + " B" : b < 1048576 ? (b / 1024).toFixed(1) + " KB" : b < 1073741824 ? (b / 1048576).toFixed(1) + " MB" : (b / 1073741824).toFixed(2) + " GB");
export const fmtDate = (d, lang = "en") => (d ? new Date(d).toLocaleString(lang === "ar" ? "ar-TN" : lang === "fr" ? "fr-FR" : "en-GB", { dateStyle: "medium", timeStyle: "short" }) : "—");

export function useAsync(fn, deps = []) {
  const [state, set] = useState({ data: null, loading: true, error: null });
  const run = useCallback(() => {
    set((s) => ({ ...s, loading: true }));
    fn().then((data) => set({ data, loading: false, error: null })).catch((e) => set({ data: null, loading: false, error: e.message }));
  }, deps); // eslint-disable-line
  useEffect(run, [run]);
  return { ...state, reload: run };
}

export const Card = ({ title, children, className = "", right }) => (
  <div className={"card " + className}>
    {(title || right) && <div className="row" style={{ justifyContent: "space-between", marginBottom: 14 }}>{title && <h3 style={{ margin: 0 }}>{title}</h3>}{right}</div>}
    {children}
  </div>
);
export const Stat = ({ icon, value, label }) => (
  <div className="card stat"><div className="ic"><Icon n={icon} /></div><div><b>{value}</b><span>{label}</span></div></div>
);
export const Badge = ({ kind, children }) => <span className={"badge b-" + kind}>{children}</span>;
export const PageHead = ({ title, sub, children }) => (
  <div className="page-head"><div><h1>{title}</h1>{sub && <p>{sub}</p>}</div><div className="row">{children}</div></div>
);
export const Empty = ({ title, hint, children }) => <div className="empty"><b>{title}</b>{hint}{children && <div style={{ marginTop: 14 }}>{children}</div>}</div>;
export const Loading = () => { const { t } = useApp(); return <div className="empty">{t("loading")}</div>; };
export const Modal = ({ title, onClose, children }) => (
  <div className="modal-bg" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
    <div className="modal" role="dialog" aria-modal="true"><h2 style={{ fontSize: 20, marginBottom: 16 }}>{title}</h2>{children}</div>
  </div>
);
export const Field = ({ label, children }) => <div className="field"><label>{label}</label>{children}</div>;
export const LangBadge = ({ code }) => <Badge kind={code}>{{ ar: "ع AR", fr: "FR", en: "EN" }[code] || code}</Badge>;
