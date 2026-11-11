const BASE = import.meta.env.VITE_API_URL || "/api";
export const token = () => localStorage.getItem("token");

function errMsg(d) {
  if (!d) return "Request failed";
  if (d.detail) return d.detail;
  const k = Object.keys(d)[0];
  const v = d[k];
  return `${k}: ${Array.isArray(v) ? v[0] : v}`;
}

async function req(path, { method = "GET", body, form } = {}) {
  const headers = {};
  if (token()) headers.Authorization = "Token " + token();
  let payload;
  if (form) payload = form;
  else if (body !== undefined) { headers["Content-Type"] = "application/json"; payload = JSON.stringify(body); }
  const r = await fetch(BASE + path, { method, headers, body: payload });
  if (r.status === 204) return null;
  const data = await r.json().catch(() => ({}));
  if (!r.ok) {
    if (r.status === 401 && token()) { localStorage.removeItem("token"); location.href = "/login"; }
    throw new Error(errMsg(data));
  }
  return data;
}

export const api = {
  get: (p) => req(p),
  post: (p, body) => req(p, { method: "POST", body }),
  put: (p, body) => req(p, { method: "PUT", body }),
  patch: (p, body) => req(p, { method: "PATCH", body }),
  del: (p) => req(p, { method: "DELETE" }),
  // multipart upload with progress
  upload(file, extra = {}, onProgress) {
    return new Promise((resolve, reject) => {
      const fd = new FormData();
      fd.append("file", file);
      Object.entries(extra).forEach(([k, v]) => v && fd.append(k, v));
      const x = new XMLHttpRequest();
      x.open("POST", BASE + "/documents/");
      x.setRequestHeader("Authorization", "Token " + token());
      x.upload.onprogress = (e) => e.lengthComputable && onProgress?.(Math.round((e.loaded / e.total) * 100));
      x.onload = () => {
        let d = {};
        try { d = JSON.parse(x.responseText); } catch {}
        x.status < 300 ? resolve(d) : reject(new Error(errMsg(d)));
      };
      x.onerror = () => reject(new Error("Network error"));
      x.send(fd);
    });
  },
};
