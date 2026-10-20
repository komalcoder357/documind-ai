import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { api, errMsg } from "../api";
import Doci, { DociState } from "../components/Doci";
import { Alert, Badge, Empty, Skeleton, fmtBytes } from "../components/ui";

const PENDING = ["queued", "validating", "extracting", "chunking", "embedding", "indexing"];

export default function Documents() {
  const [docs, setDocs] = useState<any[] | null>(null); const [err, setErr] = useState(""); const [ok, setOk] = useState(""); const [busy, setBusy] = useState(false); const [d, setD] = useState<DociState>("idle");
  const input = useRef<HTMLInputElement>(null);
  const load = useCallback(() => api("/documents").then(setDocs).catch((e) => setErr(errMsg(e))), []);
  useEffect(() => { load(); }, [load]);
  const pending = docs?.some((x) => PENDING.includes(x.status));
  useEffect(() => { if (!pending) return; const t = setInterval(load, 2000); return () => clearInterval(t); }, [pending, load]);
  useEffect(() => { setD(busy ? "thinking" : pending ? "processing" : docs && docs.length === 0 ? "empty" : "idle"); }, [busy, pending, docs]);

  async function upload(files: FileList | null) {
    if (!files?.length) return; setErr(""); setOk(""); setBusy(true);
    for (const f of Array.from(files)) {
      const fd = new FormData(); fd.append("file", f);
      try { const r = await api("/documents", { form: fd }); if (r.status === "failed") { setErr(`${f.name}: ${r.error}`); setD("concerned"); } else { setOk(`${f.name} uploaded (${r.status}).`); } }
      catch (e) { setErr(`${f.name}: ${errMsg(e)}`); setD("concerned"); }
    }
    setBusy(false); if (input.current) input.current.value = ""; load();
  }
  async function del(id: number) { if (!confirm("Delete this document and its indexed data?")) return; try { await api(`/documents/${id}`, { method: "DELETE" }); load(); } catch (e) { setErr(errMsg(e)); } }
  async function retry(doc: any) { try { const s = await api(`/documents/${doc.id}/status`); await api(`/jobs/${s.job.id}/retry`, { method: "POST" }); load(); } catch (e) { setErr(errMsg(e)); } }

  return (
    <div>
      <div className="row between"><h1>Documents</h1><Doci state={d} size={56} /></div>
      <div className="card">
        <label className="drop">Upload PDF, DOCX or TXT files (max 10 MB each)<input ref={input} type="file" multiple accept=".pdf,.docx,.txt" onChange={(e) => upload(e.target.files)} disabled={busy} /></label>
        {busy && <p className="muted">Uploading…</p>}
      </div>
      {err && <Alert>{err}</Alert>}{ok && <Alert kind="ok">{ok}</Alert>}
      {docs === null ? <Skeleton h={120} /> : docs.length === 0 ? <Empty title="No documents yet">Upload your first file above.</Empty> : (
        <div className="card table-wrap"><table><thead><tr><th>Title</th><th>Type</th><th>Size</th><th>Status</th><th></th></tr></thead><tbody>
          {docs.map((x) => <tr key={x.id}><td>{x.status === "ready" ? <Link to={`/app/documents/${x.id}`}>{x.title}</Link> : x.title}{x.warnings?.length > 0 && <div className="muted small">⚠ {x.warnings[0]}</div>}{x.error && <div className="field-err">{x.error}</div>}</td>
            <td>{x.kind.toUpperCase()}</td><td>{fmtBytes(x.size_bytes)}</td><td><Badge s={x.status} /></td>
            <td className="actions">{x.status === "failed" && <button className="btn small ghost" onClick={() => retry(x)}>Retry</button>}<button className="btn small ghost" onClick={() => del(x.id)} aria-label={`Delete ${x.title}`}>Delete</button></td></tr>)}
        </tbody></table></div>)}
    </div>
  );
}
