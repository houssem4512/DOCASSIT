import React, { useEffect, useRef, useState } from "react";
import { Link, useNavigate, useParams, useSearchParams } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import { Badge, Card, Field, Icon, Modal, useAsync } from "../components/ui.jsx";

export default function Chat() {
  const { id } = useParams();
  const nav = useNavigate();
  const { t, notify } = useApp();
  const list = useAsync(() => api.get("/conversations/"), [id]);
  const docs = useAsync(() => api.get("/documents/?status=ready"));
  const [conv, setConv] = useState(null);
  const [msgs, setMsgs] = useState([]);
  const [docIds, setDocIds] = useState([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [pick, setPick] = useState(false);
  const end = useRef();
  const [sp] = useSearchParams();
  useEffect(() => { if (sp.get("q")) setText(sp.get("q")); }, []); // eslint-disable-line

  useEffect(() => {
    if (!id) { setConv(null); setMsgs([]); setDocIds([]); return; }
    api.get(`/conversations/${id}/`).then((c) => { setConv(c); setMsgs(c.messages); setDocIds(c.document_ids); });
  }, [id]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: "smooth" }); }, [msgs, busy]);

  const send = async () => {
    const q = text.trim(); if (!q || busy) return;
    setText(""); setBusy(true);
    setMsgs((m) => [...m, { id: "tmp", role: "user", content: q }]);
    try {
      let cid = id;
      if (!cid) { const c = await api.post("/conversations/", { title: q.slice(0, 60), document_ids: docIds }); cid = c.id; }
      const r = await api.post(`/conversations/${cid}/ask/`, { question: q });
      setMsgs((m) => [...m.filter((x) => x.id !== "tmp"), r.user_message, r.assistant_message]);
      if (!id) nav("/chat/" + cid, { replace: true }); else list.reload();
    } catch (e) { notify(e.message); setMsgs((m) => m.filter((x) => x.id !== "tmp")); } finally { setBusy(false); }
  };
  const saveDocs = async (ids) => {
    setDocIds(ids); setPick(false);
    if (id) await api.patch(`/conversations/${id}/`, { document_ids: ids });
  };
  const attached = (docs.data || []).filter((d) => docIds.includes(d.id));

  return (
    <div className="chat">
      <Card className="chat-list">
        <Link to="/chat" className="btn pri" style={{ width: "100%", marginBottom: 10 }}><Icon n="plus" size={18} />{t("newChat")}</Link>
        {(list.data || []).map((c) => <Link key={c.id} to={"/chat/" + c.id} className={"chat-item" + (String(c.id) === id ? " on" : "")} dir="auto">{c.title}</Link>)}
      </Card>
      <Card className="chat-main">
        <div className="chat-head">
          <button className="btn sm" onClick={() => setPick(true)}><Icon n="paperclip" size={16} />{t("attach")}</button>
          {attached.length === 0 ? <span className="mute">{t("noAttached")}</span> : attached.map((d) => <Badge key={d.id} kind="info">{d.title}</Badge>)}
        </div>
        <div className="msgs">
          {msgs.length === 0 && <div className="empty" style={{ margin: "auto" }}><b>{t("askNow")}</b>العربية · Français · English</div>}
          {msgs.map((m, i) => (
            <div key={m.id + "-" + i} className={"bubble " + m.role} dir="auto">{m.content}
              {m.sources?.length > 0 && <div className="src"><b>{t("sources")}</b>{m.sources.map((s, k) => <div key={k}>• {s.title} · p.{s.page}</div>)}</div>}
            </div>))}
          {busy && <div className="bubble assistant typing"><span /><span /><span /></div>}
          <div ref={end} />
        </div>
        <div className="composer">
          <textarea rows={2} dir="auto" value={text} placeholder={t("askPlaceholder")} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
          <button className="btn pri" onClick={send} disabled={busy || !text.trim()}><Icon n="send" size={18} />{t("send")}</button>
        </div>
      </Card>
      {pick && <PickDocs docs={docs.data || []} sel={docIds} onSave={saveDocs} onClose={() => setPick(false)} />}
    </div>
  );
}

function PickDocs({ docs, sel, onSave, onClose }) {
  const { t } = useApp();
  const [s, setS] = useState(sel);
  const toggle = (i) => setS(s.includes(i) ? s.filter((x) => x !== i) : [...s, i]);
  return (
    <Modal title={t("attach")} onClose={onClose}>
      <div style={{ maxHeight: 320, overflow: "auto" }}>{docs.map((d) => (
        <label key={d.id} className="list-item" style={{ cursor: "pointer" }}><input type="checkbox" checked={s.includes(d.id)} onChange={() => toggle(d.id)} /><span className="grow t" dir="auto">{d.title}</span></label>))}
        {docs.length === 0 && <div className="mute">{t("noDocs")}</div>}</div>
      <div className="row" style={{ justifyContent: "flex-end", marginTop: 16 }}><button className="btn" onClick={onClose}>{t("cancel")}</button><button className="btn pri" onClick={() => onSave(s)}>{t("save")}</button></div>
    </Modal>
  );
}
