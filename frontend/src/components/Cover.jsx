import React, { useEffect, useState } from "react";
import { useApp } from "../App.jsx";

const SAMPLES = {
  ar: { dir: "rtl", q: "ما هي مدة العقد وشروط التجديد؟", a: "مدة العقد 36 شهراً، وتجدد تلقائياً ما لم يُخطر أحد الطرفين الآخر قبل 60 يوماً.", src: "contrat.pdf · ص 4" },
  fr: { dir: "ltr", q: "Quelle est la date limite de paiement ?", a: "Le paiement est exigible sous 30 jours à compter de la date de facture.", src: "facture.pdf · p. 2" },
  en: { dir: "ltr", q: "What are the termination conditions?", a: "Either party may terminate with 60 days’ written notice after the initial term.", src: "agreement.docx · p. 7" },
};
const ORDER = ["ar", "fr", "en"];

export default function Cover({ className = "" }) {
  const { lang } = useApp();
  const [i, setI] = useState(Math.max(0, ORDER.indexOf(lang)));
  const [n, setN] = useState(0);
  useEffect(() => { setI(Math.max(0, ORDER.indexOf(lang))); setN(0); }, [lang]); // start with the UI language
  const s = SAMPLES[ORDER[i]];
  useEffect(() => {
    if (n < s.q.length) { const id = setTimeout(() => setN(n + 1), 55); return () => clearTimeout(id); }
    const id = setTimeout(() => { setI((i + 1) % ORDER.length); setN(0); }, 4200);
    return () => clearTimeout(id);
  }, [n, i]); // eslint-disable-line
  const done = n >= s.q.length;
  return (
    <div className={className}>
      <div className="cover" aria-hidden="true">
        <div className="orbit o1"><span className="chip">ع</span><span className="chip c2">FR</span></div>
        <div className="orbit o2"><span className="chip">EN</span><span className="chip c2">ض</span></div>
        <div className="orbit o3"><span className="chip">é</span></div>
        <div className="core">L</div>
        <div className="fl fl-doc">
          <div className="ln" style={{ width: "60%" }} /><div className="ln" /><div className="ln hl" /><div className="ln" style={{ width: "80%" }} /><div className="ln" /><div className="ln hl" style={{ animationDelay: "-1.2s" }} />
        </div>
        <div className="fl fl-src">
          <div className="mute">{done ? s.src : "…"}</div>
          <div className="meter" style={{ marginTop: 8 }}><div style={{ width: done ? "92%" : "10%" }} /></div>
        </div>
        <div className="fl fl-chat" dir={s.dir}>
          <div className="q">{s.q.slice(0, n)}<span className="caret" /></div>
          {done && <div className="a" key={i}>{s.a}</div>}
        </div>
      </div>
    </div>
  );
}
