import React, { useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Card, Icon, PageHead } from "../components/ui.jsx";

export default function UploadPage() {
  const { t, notify, refreshUnread } = useApp();
  const input = useRef();
  const [items, setItems] = useState([]); // {file, progress, state, error}
  const [language, setLanguage] = useState("");
  const [over, setOver] = useState(false);
  const add = (files) => setItems((p) => [...p, ...[...files].map((file) => ({ file, progress: 0, state: "queued" }))]);
  const patch = (i, o) => setItems((p) => p.map((x, k) => (k === i ? { ...x, ...o } : x)));
  const start = async () => {
    for (let i = 0; i < items.length; i++) {
      if (items[i].state !== "queued") continue;
      patch(i, { state: "uploading" });
      try { await api.upload(items[i].file, { language }, (p) => patch(i, { progress: p })); patch(i, { state: "done", progress: 100 }); }
      catch (e) { patch(i, { state: "error", error: e.message }); }
    }
    notify(t("uploaded") + " ✓"); refreshUnread();
  };
  return (
    <>
      <PageHead title={t("upload")} sub={t("allowed")}><select className="inp" value={language} onChange={(e) => setLanguage(e.target.value)}><option value="">{t("autoDetect")}</option><option value="ar">العربية</option><option value="fr">Français</option><option value="en">English</option></select></PageHead>
      <Card>
        <div className={"drop" + (over ? " over" : "")} onClick={() => input.current.click()} onDragOver={(e) => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={(e) => { e.preventDefault(); setOver(false); add(e.dataTransfer.files); }}>
          <Icon n="upload" size={34} /><h3 style={{ margin: "10px 0 4px" }}>{t("dropHere")}</h3><span className="mute">{t("allowed")}</span>
          <input ref={input} type="file" multiple hidden onChange={(e) => { add(e.target.files); e.target.value = ""; }} />
        </div>
      </Card>
      {items.length > 0 && (
        <Card title={t("queue")} className="" right={<button className="btn pri" onClick={start} disabled={!items.some((x) => x.state === "queued")}>{t("startUpload")}</button>}>
          {items.map((x, i) => (
            <div className="list-item" key={i}><div className="file-ic"><Icon n="file" /></div>
              <div className="grow"><div className="t" dir="auto">{x.file.name}</div>
                <div className="meter" style={{ marginTop: 6 }}><div style={{ width: x.progress + "%", background: x.state === "error" ? "var(--bad)" : undefined }} /></div>
                {x.error && <div className="err" style={{ margin: "4px 0 0" }}>{x.error}</div>}</div>
              <span className="mute">{x.state === "done" ? "✓" : x.state === "uploading" ? x.progress + "%" : ""}</span>
              {x.state === "queued" && <button className="icon-btn" onClick={() => setItems(items.filter((_, k) => k !== i))}><Icon n="trash" size={16} /></button>}</div>))}
          {items.every((x) => x.state === "done") && <div style={{ marginTop: 14 }}><Link to="/documents" className="btn">{t("documents")}</Link></div>}
        </Card>)}
    </>
  );
}
