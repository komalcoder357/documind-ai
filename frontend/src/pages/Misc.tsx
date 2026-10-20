import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, errMsg } from "../api";
import { useAuth } from "../auth";
import { Alert, Empty, Skeleton, fmtBytes } from "../components/ui";

export function Reports() {
  const [l, setL] = useState<any[] | null>(null); const [err, setErr] = useState("");
  const load = () => api("/reports").then(setL).catch((e) => setErr(errMsg(e))); useEffect(() => { load(); }, []);
  async function del(id: number) { if (confirm("Delete this report?")) { try { await api(`/reports/${id}`, { method: "DELETE" }); load(); } catch (e) { setErr(errMsg(e)); } } }
  return <div><h1>Reports</h1>{err && <Alert>{err}</Alert>}{l === null ? <Skeleton h={80} /> : l.length === 0 ? <Empty title="No saved reports">Export a candidate comparison or save a document comparison to see it here.</Empty> :
    l.map((r) => <div className="card row between" key={r.id}><div><b>{r.title}</b><div className="muted small">{r.kind} · {new Date(r.created_at).toLocaleString()}</div></div>
      <div className="row"><a className="btn small ghost" href={`/api/v1/reports/${r.id}/download?format=docx`}>Word</a>{r.kind === "candidate_comparison" && <a className="btn small ghost" href={`/api/v1/reports/${r.id}/download?format=csv`}>CSV</a>}<a className="btn small ghost" href={`/api/v1/reports/${r.id}/download?format=json`}>JSON</a><button className="btn small ghost" onClick={() => del(r.id)}>Delete</button></div></div>)}</div>;
}

export function Settings({ replay }: { replay: () => void }) {
  const { user, setUser } = useAuth(); const nav = useNavigate(); const [pw, setPw] = useState(""); const [err, setErr] = useState(""); const [ok, setOk] = useState("");
  const save = async (p: any) => { try { setUser(await api("/me/preferences", { method: "PUT", body: p })); setOk("Preferences saved."); } catch (e) { setErr(errMsg(e)); } };
  async function del() { if (!confirm("Permanently delete your account and all your data?")) return; try { await api("/me", { method: "DELETE", body: { password: pw } }); setUser(null); nav("/"); } catch (e) { setErr(errMsg(e)); } }
  return <div><h1>Settings</h1>{err && <Alert>{err}</Alert>}{ok && <Alert kind="ok">{ok}</Alert>}
    <div className="card"><h3>Profile</h3><p>{user?.full_name} · {user?.email}</p></div>
    <div className="card"><h3>Appearance</h3><label className="check"><input type="checkbox" checked={user?.prefs.theme === "dark"} onChange={(e) => save({ theme: e.target.checked ? "dark" : "light" })} /> Dark theme</label>
      <label className="check"><input type="checkbox" checked={!!user?.prefs.reduced_motion} onChange={(e) => save({ reduced_motion: e.target.checked })} /> Reduce motion (animations also follow your system setting)</label>
      <button className="btn ghost small" onClick={replay}>Replay the guided walkthrough</button></div>
    <div className="card"><h3>Delete account</h3><p className="muted">Removes your account, files, indexed text, embeddings, projects and reports.</p><label>Confirm password<input type="password" value={pw} onChange={(e) => setPw(e.target.value)} /></label><button className="btn danger" onClick={del} disabled={!pw}>Delete my account</button></div></div>;
}

export function Admin() {
  const [s, setS] = useState<any>(null); const [users, setUsers] = useState<any[]>([]); const [audit, setAudit] = useState<any[]>([]); const [h, setH] = useState<any>(null); const [err, setErr] = useState("");
  const load = () => Promise.all([api("/admin/stats"), api("/admin/users"), api("/admin/audit"), api("/admin/health")]).then(([a, b, c, d]) => { setS(a); setUsers(b); setAudit(c); setH(d); }).catch((e) => setErr(errMsg(e)));
  useEffect(() => { load(); }, []);
  async function toggle(u: any) { try { await api(`/admin/users/${u.id}/${u.is_active ? "suspend" : "reactivate"}`, { method: "POST" }); load(); } catch (e) { setErr(errMsg(e)); } }
  if (err) return <Alert>{err}</Alert>; if (!s) return <Skeleton h={200} />;
  const stats: [string, any][] = [["Users", s.users_total], ["Active (7 days)", s.active_users_7d], ["Workspaces", s.workspaces], ["Documents uploaded", s.documents_uploaded], ["Documents processed", s.documents_processed], ["Failed jobs", s.failed_jobs], ["CV analyses", s.cv_analyses_completed], ["Storage", fmtBytes(s.storage_bytes)], ["Avg job time", s.avg_job_seconds == null ? "n/a" : s.avg_job_seconds + " s"]];
  return <div><h1>Admin</h1><div className="grid3">{stats.map(([k, v]) => <div className="card stat" key={k}><div className="muted">{k}</div><div className="big">{v}</div></div>)}</div><p className="muted small">{s.window}</p>
    <div className="card"><h3>Service health</h3><pre className="small">{JSON.stringify(h, null, 2)}</pre></div>
    <div className="card table-wrap"><h3>Users</h3><table><thead><tr><th>Email</th><th>Role</th><th>Active</th><th></th></tr></thead><tbody>{users.map((u) => <tr key={u.id}><td>{u.email}</td><td>{u.role}</td><td>{u.is_active ? "yes" : "suspended"}</td><td><button className="btn small ghost" onClick={() => toggle(u)}>{u.is_active ? "Suspend" : "Reactivate"}</button></td></tr>)}</tbody></table></div>
    <div className="card table-wrap"><h3>Audit log</h3><table><thead><tr><th>Time</th><th>User</th><th>Action</th></tr></thead><tbody>{audit.slice(0, 50).map((a) => <tr key={a.id}><td>{new Date(a.created_at).toLocaleString()}</td><td>{a.user_id ?? "—"}</td><td>{a.action}</td></tr>)}</tbody></table></div></div>;
}
