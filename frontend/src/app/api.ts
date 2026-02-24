export const API_BASE = "/api";
export function getToken(): string | null { return localStorage.getItem("token"); }

export async function apiGet(path: string) {
  const token = getToken();
  const r = await fetch(`${API_BASE}${path}`, { headers: token ? { Authorization: `Bearer ${token}` } : {} });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function apiPost(path: string, body: any) {
  const token = getToken();
  const r = await fetch(`${API_BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type":"application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}) },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function apiUpload(path: string, file: File) {
  const token = getToken();
  const fd = new FormData();
  fd.append("file", file);
  const r = await fetch(`${API_BASE}${path}`, { method: "POST", headers: token ? { Authorization: `Bearer ${token}` } : {}, body: fd });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}
