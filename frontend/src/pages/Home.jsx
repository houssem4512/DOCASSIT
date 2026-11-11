import React from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api.js";
import { useApp } from "../App.jsx";
import Cover from "../components/Cover.jsx";
import { Donut } from "../components/charts.jsx";
import { LangSwitch, ThemeToggle } from "../components/Layout.jsx";
import { Badge, Card, Empty, fmtBytes, fmtDate, Icon, LangBadge, Loading, Stat, useAsync } from "../components/ui.jsx";

const HELLO = ["مرحباً", "Bonjour", "Hello", "أهلاً بك", "Bienvenue", "Welcome", "شكراً", "Merci", "Thank you"];

export default function Home() {
  const { t, user, lang } = useApp();
  const nav = useNavigate();
  const { data: d, loading } = useAsync(() => api.get("/dashboard/"));
  if (loading || !d) return <Loading />;
  const h = new Date().getHours();
  const greet = h < 12 ? t("greetMorning") : h < 18 ? t("greetDay") : t("greetEvening");
  const L = d.by_language;
  return (
    <div className="grid" style={{ gap: 22 }}>
      <div className="card hero2">
        <div className="hero-ctl"><LangSwitch /><ThemeToggle /></div>
        <div className="hero2-l">
          <span className="pill"><i />{greet}, {user.first_name || user.username}</span>
          <h2>{t("heroTitle")}</h2>
          <p>{t("heroSub")}</p>
          <div className="row"><Link to="/upload" className="btn pri"><Icon n="upload" size={18} />{t("uploadDoc")}</Link><Link to="/chat" className="btn"><Icon n="chat" size={18} />{t("askNow")}</Link></div>
        </div>
        <div className="hero2-r"><Cover /></div>
      </div>

      <div className="marquee" aria-hidden="true"><div className="track">{[...HELLO, ...HELLO].map((w, i) => <span key={i}>{w} <b>✦</b></span>)}</div></div>

      <div className="grid g3">
        <Link to="/upload" className="tile t1"><Icon n="upload" size={26} /><b>{t("quickUpload")}</b><span>{t("quickUploadSub")}</span><i className="big">ع</i></Link>
        <Link to="/search" className="tile t2"><Icon n="search" size={26} /><b>{t("quickSearch")}</b><span>{t("quickSearchSub")}</span><i className="big">é</i></Link>
        <Link to="/chat" className="tile t3"><Icon n="chat" size={26} /><b>{t("quickAsk")}</b><span>{t("quickAskSub")}</span><i className="big">?</i></Link>
      </div>

      <div className="grid g4">
        <Stat icon="file" value={d.documents} label={t("docsCount")} />
        <Stat icon="check" value={d.ready} label={t("ready")} />
        <Stat icon="chat" value={d.questions} label={t("questions")} />
        <Stat icon="db" value={fmtBytes(d.storage)} label={t("storage")} />
      </div>

      <div className="grid g21">
        <Card title={t("recentDocs")} right={<Link to="/documents" className="mute">{t("documents")}</Link>}>
          {d.recent_documents.length === 0 ? <Empty title={t("noDocs")} hint={t("noDocsHint")} /> : d.recent_documents.map((x) => (
            <div className="list-item" key={x.id}><div className="file-ic"><Icon n="pdf" /></div>
              <div className="grow"><div className="t" dir="auto">{x.title}</div><div className="mute">{fmtBytes(x.size)} · {fmtDate(x.created_at, lang)}</div></div>
              <LangBadge code={x.language} /><Badge kind={x.status}>{t(x.status)}</Badge></div>))}
        </Card>
        <Card title={t("docsLanguages")}>
          <Donut size={150} center={d.documents} data={[{ label: "العربية", value: L.ar, color: "#7c5cff" }, { label: "Français", value: L.fr, color: "#ff4fa3" }, { label: "English", value: L.en, color: "#22d3ee" }]} />
        </Card>
      </div>

      <div className="grid g2">
        <Card title={t("tipsTitle")}>
          {["tip1", "tip2", "tip3"].map((k) => <button key={k} className="tip" dir="auto" onClick={() => nav("/chat?q=" + encodeURIComponent(t(k)))}>{t(k)}</button>)}
        </Card>
        <Card title={t("recentChats")}>
          {d.recent_conversations.length === 0 ? <div className="mute">{t("noChats")}</div> : d.recent_conversations.map((c) => (
            <Link to={"/chat/" + c.id} className="list-item" key={c.id}><Icon n="chat" size={18} /><div className="grow t" dir="auto">{c.title}</div></Link>))}
        </Card>
      </div>
    </div>
  );
}
