import React from "react";

const GLYPHS = "ع ب ت ج د ر س ش ص ق é è ç à ô ù A B C ¶ § ي م ن".split(" ");
export default function Aurora() {
  return (
    <div className="bg" aria-hidden="true">
      <i className="blob b1" /><i className="blob b2" /><i className="blob b3" />
      <div className="gridfx" />
      {GLYPHS.map((g, i) => (
        <span key={i} className="glyph" style={{ left: ((i * 37) % 96) + "%", animationDelay: -(i * 3.7) + "s", animationDuration: 20 + (i % 6) * 4 + "s", fontSize: 20 + (i % 5) * 11 + "px" }}>{g}</span>
      ))}
    </div>
  );
}
