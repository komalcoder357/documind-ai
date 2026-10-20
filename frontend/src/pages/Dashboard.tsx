import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { api, errMsg } from "../api";
import { Alert, Badge, Empty, Skeleton, fmtBytes } from "../components/ui";

export default function Dashboard() {
  const [d, setD] = useState<any>(null); const [err, setErr] = useState("");
  useEffect(() => { api("/dashboard").then(setD).catch((e) => setErr(errMsg(e))); }, []);
  if (err) return <Alert>{err}</Alert>;
  if (!d) return <div><Skeleton h={90} /><Skeleton h={90} /></div>;
  const stats: [string, string | number][] = [["Documents", d.documents_total], ["Ready", d.documents_ready], ["Processing", d.documents_pending], ["CVs analyzed", d.cvs_analyzed], ["Storage used", fmtBytes(d.storage_bytes)], ["Running jobs", d.running_jobs]];
  return (
    <div>
      <h1>Dashboard</h1>
      <div className="grid3">{stats.map(([k, v]) => <div className="card stat" key={k}><div className="muted">{k}</div><div className="big">{v}</div></div>)}</div>
      {d.documents_total === 0 && d.recent_projects.length === 0 ? <Empty title="Welcome! Nothing here yet.">Upload a document or create a recruitment project to begin.</Empty> : null}
      <div className="grid2">
        <div className="card"><h3>Recent documents</h3>{d.recent_documents.length ? d.recent_documents.map((x: any) => <p key={x.id}><Link to={`/app/documents/${x.id}`}>{x.title}</Link> <Badge s={x.status} /></p>) : <p className="muted">No documents yet.</p>}</div>
        <div className="card"><h3>Recent recruitment projects</h3>{d.recent_projects.length ? d.recent_projects.map((x: any) => <p key={x.id}><Link to={`/app/recruitment/${x.id}`}>{x.title}</Link> <span className="muted">{x.job_title}</span></p>) : <p className="muted">No projects yet.</p>}</div>
      </div>
      <div className="row"><Link className="btn" to="/app/documents">Upload a document</Link><Link className="btn ghost" to="/app/recruitment">New recruitment project</Link><Link className="btn ghost" to="/app/compare">Compare documents</Link></div>
    </div>
  );
}
