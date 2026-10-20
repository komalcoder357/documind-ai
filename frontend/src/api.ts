export class ApiError extends Error { status: number; constructor(m: string, s: number) { super(m); this.status = s; } }
export const csrf = () => document.cookie.split("; ").find((r) => r.startsWith("csrf="))?.split("=")[1] ?? "";

export async function api<T = any>(path: string, o: { method?: string; body?: unknown; form?: FormData } = {}): Promise<T> {
  const method = o.method ?? (o.body || o.form ? "POST" : "GET");
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;
  if (o.form) body = o.form; else if (o.body !== undefined) { headers["Content-Type"] = "application/json"; body = JSON.stringify(o.body); }
  if (method !== "GET") headers["X-CSRF-Token"] = csrf();
  let r: Response;
  try { r = await fetch("/api/v1" + path, { method, headers, body, credentials: "include" }); }
  catch { throw new ApiError("Cannot reach the server. Check your connection and try again.", 0); }
  if (!r.ok) {
    let msg = r.statusText || "Request failed";
    try { const j = await r.json(); msg = typeof j.detail === "string" ? j.detail : Array.isArray(j.detail) ? j.detail.map((d: any) => d.msg).join("; ") : msg; } catch { /* ignore */ }
    throw new ApiError(msg, r.status);
  }
  return r.json();
}
export const errMsg = (e: unknown) => (e instanceof Error ? e.message : "Something went wrong");
