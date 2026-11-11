import React, { useId, useState } from "react";

export const PALETTE = ["#7c5cff", "#ff4fa3", "#22d3ee", "#f59e0b", "#16a37a", "#3b82f6"];

export function LineChart({ labels, series, height = 230 }) {
  const gid = useId().replace(/:/g, "");
  const [hi, setHi] = useState(null);
  const W = 640, H = height, L = 30, B = 24, T = 10, R = 8, n = labels.length;
  const max = Math.max(1, ...series.flatMap((s) => s.values));
  const top = Math.max(4, Math.ceil(max / 4) * 4);
  const x = (i) => L + (n <= 1 ? 0 : (i * (W - L - R)) / (n - 1));
  const y = (v) => T + (1 - v / top) * (H - T - B);
  const line = (vals) => vals.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(" ");
  const step = Math.ceil(n / 7);
  const move = (e) => {
    const r = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    setHi(Math.max(0, Math.min(n - 1, Math.round(((px - L) / (W - L - R)) * (n - 1)))));
  };
  return (
    <div style={{ position: "relative" }} dir="ltr">
      <svg viewBox={`0 0 ${W} ${H}`} width="100%" onMouseMove={move} onMouseLeave={() => setHi(null)} style={{ display: "block" }}>
        <defs>{series.map((s, k) => (
          <linearGradient key={k} id={`${gid}${k}`} x1="0" x2="0" y1="0" y2="1"><stop offset="0" stopColor={s.color} stopOpacity=".35" /><stop offset="1" stopColor={s.color} stopOpacity="0" /></linearGradient>))}</defs>
        {[0, 1, 2, 3, 4].map((g) => { const v = (top / 4) * g; return <g key={g}><line x1={L} x2={W - R} y1={y(v)} y2={y(v)} stroke="currentColor" opacity=".1" /><text x={L - 6} y={y(v) + 4} fontSize="10" textAnchor="end" fill="currentColor" opacity=".55">{Math.round(v)}</text></g>; })}
        {labels.map((l, i) => i % step === 0 && <text key={i} x={x(i)} y={H - 6} fontSize="10" textAnchor="middle" fill="currentColor" opacity=".55">{l.slice(5)}</text>)}
        {series.map((s, k) => <path key={"a" + k} d={`${line(s.values)} L${x(n - 1)},${H - B} L${x(0)},${H - B}Z`} fill={`url(#${gid}${k})`} />)}
        {series.map((s, k) => <path key={"l" + k} d={line(s.values)} fill="none" stroke={s.color} strokeWidth="2.4" strokeLinejoin="round" strokeLinecap="round" />)}
        {hi !== null && <g><line x1={x(hi)} x2={x(hi)} y1={T} y2={H - B} stroke="currentColor" opacity=".25" />{series.map((s, k) => <circle key={k} cx={x(hi)} cy={y(s.values[hi])} r="4.5" fill={s.color} stroke="#fff" strokeWidth="1.5" />)}</g>}
        <rect x="0" y="0" width={W} height={H} fill="transparent" />
      </svg>
      {hi !== null && (
        <div className="chart-tip" style={{ left: `${Math.min(78, Math.max(0, (x(hi) / W) * 100 - 8))}%`, top: 0 }}>
          <b>{labels[hi]}</b>{series.map((s) => <div key={s.name}><span style={{ color: s.color }}>●</span> {s.name}: <b>{s.values[hi]}</b></div>)}
        </div>)}
      <div className="row" style={{ gap: 14, marginTop: 6 }}>{series.map((s) => <span key={s.name} className="mute"><span style={{ color: s.color }}>●</span> {s.name}</span>)}</div>
    </div>
  );
}

export function Donut({ data, size = 140, center }) {
  const total = data.reduce((a, d) => a + d.value, 0);
  let acc = 0;
  const stops = total ? data.map((d, i) => { const a = acc, b = acc + (d.value / total) * 100; acc = b; return `${d.color || PALETTE[i % 6]} ${a}% ${b}%`; }).join(",") : "var(--line) 0 100%";
  return (
    <div className="row" style={{ gap: 22 }}>
      <div style={{ position: "relative" }}>
        <div className="donut" style={{ width: size, height: size, "--hole": size * 0.66 + "px", background: `conic-gradient(${stops})` }} />
        <div style={{ position: "absolute", inset: 0, display: "grid", placeItems: "center", textAlign: "center", fontWeight: 800, fontSize: 20 }}>{center ?? total}</div>
      </div>
      <div className="legend">{data.map((d, i) => <div key={d.label}><i style={{ background: d.color || PALETTE[i % 6] }} />{d.label} <b>{d.value}</b></div>)}</div>
    </div>
  );
}

export function Columns({ values, labels }) {
  const max = Math.max(1, ...values), pk = values.indexOf(Math.max(...values));
  return (
    <div dir="ltr"><div className="cols">{values.map((v, i) => <div key={i} className={"c" + (i === pk && v > 0 ? " pk" : "")} style={{ height: (v / max) * 100 + "%" }} title={`${labels[i]}: ${v}`} />)}</div>
      <div className="cols-l"><span>{labels[0]}</span><span>{labels[Math.floor(labels.length / 2)]}</span><span>{labels[labels.length - 1]}</span></div></div>
  );
}

export function HBars({ rows }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return rows.map((r) => (
    <div className="hrow" key={r.label}><span className="lab" title={r.label}>{r.label}</span><div className="meter"><div style={{ width: (r.value / max) * 100 + "%" }} /></div><span className="v">{r.text ?? r.value}</span></div>
  ));
}

export function Spark({ values, color = "#7c5cff", w = 90, h = 34 }) {
  const max = Math.max(1, ...values), n = values.length;
  const pts = values.map((v, i) => `${(i * w) / Math.max(1, n - 1)},${h - 3 - (v / max) * (h - 8)}`).join(" ");
  return <svg className="spark" width={w} height={h} viewBox={`0 0 ${w} ${h}`} aria-hidden="true"><polyline points={pts} fill="none" stroke={color} strokeWidth="2.2" strokeLinecap="round" strokeLinejoin="round" /></svg>;
}

export function Delta({ cur, prev }) {
  const d = prev ? Math.round(((cur - prev) / prev) * 100) : cur ? 100 : 0;
  return <span className={"delta " + (d > 0 ? "up" : d < 0 ? "down" : "flat")}>{d > 0 ? "▲" : d < 0 ? "▼" : "●"} {Math.abs(d)}%</span>;
}
