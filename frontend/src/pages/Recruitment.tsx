import { FormEvent, useCallback, useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { Bar, BarChart, CartesianGrid, Legend, PolarAngleAxis, PolarGrid, PolarRadiusAxis, Radar, RadarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api, errMsg } from "../api";
import Doci, { DociState } from "../components/Doci";
import { Alert, Badge, Empty, Skeleton } from "../components/ui";

const COLORS = ["#0f766e", "#b45309", "#4f46e5", "#be123c", "#0369a1"];
const STATUS_LABEL: Record<string, string> = { supported_by_work_sample: "Supported by work sample", listed_in_cv: "Listed in CV", partial: "Partially supported", not_found: "Not found", unable_to_verify: "Unable to verify" };

export function Projects() {
  const nav = useNavigate(); const [list, setList] = useState<any[] | null>(null); const [err, setErr] = useState("");
  const [f, setF] = useState({ title: "", job_title: "", job_description: "", required: "", preferred: "", min_years: "", education: "" });
  const load = () => api("/recruitment/projects").then(setList).catch((e) => setErr(errMsg(e)));
  useEffect(() => { load(); }, []);
  const csv = (s: string) => s.split(",").map((x) => x.trim()).filter(Boolean);
  async function create(e: FormEvent) {
    e.preventDefault(); setErr("");
    try { const p = await api("/recruitment/projects", { body: { title: f.title, job_title: f.job_title, job_description: f.job_description, required_skills: csv(f.required), preferred_skills: csv(f.preferred), min_years: f.min_years ? Number(f.min_years) : null, education: f.education || null } }); nav(`/app/recruitment/${p.id}`); }
    catch (x) { setErr(errMsg(x)); }
  }
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.value });
  return (
    <div><h1>Recruitment</h1>
      <form className="card" onSubmit={create}><h3>New recruitment project</h3>{err && <Alert>{err}</Alert>}
        <div className="grid2"><label>Project title<input value={f.title} onChange={set("title")} required /></label><label>Job title<input value={f.job_title} onChange={set("job_title")} required /></label></div>
        <label>Job description<textarea rows={4} value={f.job_description} onChange={set("job_description")} /></label>
        <div className="grid2"><label>Required skills (comma separated)<input value={f.required} onChange={set("required")} placeholder="Python, SQL" /></label><label>Preferred skills<input value={f.preferred} onChange={set("preferred")} placeholder="Docker" /></label></div>
        <div className="grid2"><label>Minimum years of experience<input type="number" min={0} max={50} value={f.min_years} onChange={set("min_years")} /></label>
          <label>Education requirement<select value={f.education} onChange={set("education")}><option value="">None</option><option value="diploma">Diploma</option><option value="bachelor">Bachelor</option><option value="master">Master</option><option value="phd">PhD</option></select></label></div>
        <p className="muted small">You can review and edit all criteria and weights before any CV is analyzed.</p><button className="btn" disabled={!f.title || !f.job_title}>Create project</button></form>
      <h3>Your projects</h3>{list === null ? <Skeleton h={60} /> : list.length === 0 ? <Empty title="No projects yet">Create one above.</Empty> : list.map((p) => <div className="card" key={p.id}><Link to={`/app/recruitment/${p.id}`}><b>{p.title}</b></Link> <span className="muted">· {p.job_title} · {p.criteria.length} criteria</span></div>)}
    </div>
  );
}

export function Project() {
  const id = Number(useParams().id); const [proj, setProj] = useState<any>(null); const [crit, setCrit] = useState<any[]>([]); const [res, setRes] = useState<any>(null);
  const [err, setErr] = useState(""); const [msg, setMsg] = useState(""); const [busy, setBusy] = useState(false); const [portfolio, setPortfolio] = useState(true); const [d, setD] = useState<DociState>("idle"); const [sort, setSort] = useState("overall"); const [fstatus, setFstatus] = useState("");
  const loadRes = useCallback(() => api(`/recruitment/projects/${id}/results?sort=${sort}${fstatus ? `&status=${fstatus}` : ""}`).then(setRes).catch((e) => setErr(errMsg(e))), [id, sort, fstatus]);
  useEffect(() => { api(`/recruitment/projects/${id}`).then((p) => { setProj(p); setCrit(p.criteria); }).catch((e) => setErr(errMsg(e))); }, [id]);
  useEffect(() => { loadRes(); }, [loadRes]);
  const working = res?.candidates.some((c: any) => ["queued", "analyzing"].includes(c.status));
  useEffect(() => { if (!working) return; const t = setInterval(loadRes, 2000); return () => clearInterval(t); }, [working, loadRes]);
  useEffect(() => { setD(working ? "processing" : res?.candidates.some((c: any) => c.status === "analyzed") ? "comparing" : "idle"); }, [working, res]);

  const upd = (i: number, k: string, v: any) => setCrit(crit.map((c, j) => (j === i ? { ...c, [k]: v } : c)));
  async function saveCrit() { setErr(""); setMsg(""); try { const r = await api(`/recruitment/projects/${id}/criteria`, { body: crit.map((c) => ({ type: c.type, level: c.level, target: c.type === "experience" ? String(c.target) : c.target, aliases: c.aliases || [], weight: Number(c.weight) })) }); setCrit(r.criteria); setMsg("Criteria saved."); } catch (e) { setErr(errMsg(e)); } }
  async function upload(files: FileList | null) {
    if (!files?.length) return; setErr(""); setMsg(""); setBusy(true); const fd = new FormData(); Array.from(files).forEach((f) => fd.append("files", f));
    try { const r = await api(`/recruitment/projects/${id}/candidates`, { form: fd }); const bad = r.results.filter((x: any) => x.status === "rejected"); setMsg(`${r.results.length - bad.length} CV(s) uploaded.`); if (bad.length) setErr(bad.map((b: any) => `${b.filename}: ${b.error}`).join(" | ")); loadRes(); } catch (e) { setErr(errMsg(e)); } setBusy(false);
  }
  async function analyze() { setErr(""); setMsg(""); try { await api(`/recruitment/projects/${id}/analyze`, { body: { check_portfolio: portfolio } }); setMsg("Analysis started."); loadRes(); } catch (e) { setErr(errMsg(e)); } }
  async function exportIt(fmt: string) { try { const r = await api(`/recruitment/projects/${id}/export`, { method: "POST" }); window.open(`/api/v1/reports/${r.report_id}/download?format=${fmt}`, "_blank"); } catch (e) { setErr(errMsg(e)); } }
  if (!proj) return err ? <Alert>{err}</Alert> : <Skeleton h={200} />;
  const analyzed = res?.candidates.filter((c: any) => c.status === "analyzed") ?? [];
  return (
    <div><div className="row between"><div><h1>{proj.title}</h1><p className="muted">{proj.job_title}</p></div><Doci state={d} size={64} /></div>
      {err && <Alert>{err}</Alert>}{msg && <Alert kind="ok">{msg}</Alert>}
      <div className="card"><h3>1. Job criteria</h3><p className="muted small">Weights are visible and editable. {res?.formula}</p>
        <div className="table-wrap"><table><thead><tr><th>Type</th><th>Level</th><th>Target</th><th>Weight</th><th></th></tr></thead><tbody>{crit.map((c, i) => <tr key={i}>
          <td><select aria-label="Criterion type" value={c.type} onChange={(e) => upd(i, "type", e.target.value)}><option>skill</option><option>keyword</option><option>experience</option><option>education</option></select></td>
          <td><select aria-label="Level" value={c.level} onChange={(e) => upd(i, "level", e.target.value)}><option>required</option><option>preferred</option></select></td>
          <td>{c.type === "education" ? <select aria-label="Education level" value={c.target} onChange={(e) => upd(i, "target", e.target.value)}><option>diploma</option><option>bachelor</option><option>master</option><option>phd</option></select> : <input aria-label="Target" value={c.target} onChange={(e) => upd(i, "target", e.target.value)} />}</td>
          <td><input aria-label="Weight" type="number" min={0.5} max={10} step={0.5} value={c.weight} onChange={(e) => upd(i, "weight", e.target.value)} style={{ width: 70 }} /></td>
          <td><button className="btn small ghost" onClick={() => setCrit(crit.filter((_, j) => j !== i))}>Remove</button></td></tr>)}</tbody></table></div>
        <div className="row"><button className="btn ghost small" onClick={() => setCrit([...crit, { type: "skill", level: "required", target: "", weight: 1, aliases: [] }])}>Add criterion</button><button className="btn small" onClick={saveCrit} disabled={!crit.length || crit.some((c) => String(c.target).trim() === "")}>Save criteria</button></div></div>
      <div className="card"><h3>2. Upload CVs</h3><label className="drop">PDF, DOCX or TXT, up to 30 files<input type="file" multiple accept=".pdf,.docx,.txt" onChange={(e) => upload(e.target.files)} disabled={busy} /></label></div>
      <div className="card"><h3>3. Analyze</h3><label className="check"><input type="checkbox" checked={portfolio} onChange={(e) => setPortfolio(e.target.checked)} /> Check public GitHub links through the official API (LinkedIn/other pages are never scraped)</label>
        <button className="btn" onClick={analyze} disabled={!res?.candidates.length || working}>{working ? "Analyzing…" : "Analyze all candidates"}</button></div>
      {res && res.candidates.length > 0 && <div className="card"><div className="row between"><h3>Candidates</h3><div className="row"><label className="inline">Sort<select value={sort} onChange={(e) => setSort(e.target.value)}><option value="overall">Match score</option><option value="filename">File name</option></select></label>
        <label className="inline">Status<select value={fstatus} onChange={(e) => setFstatus(e.target.value)}><option value="">All</option><option>analyzed</option><option>uploaded</option><option>failed</option></select></label></div></div>
        <Alert kind="info">{res.disclaimer}</Alert>
        <div className="table-wrap"><table><thead><tr><th>Candidate file</th><th>Status</th><th>Match score</th><th>Evidence coverage</th>{proj.criteria.map((c: any) => <th key={c.id}>{c.name}</th>)}</tr></thead><tbody>
          {res.candidates.map((c: any) => { const by: any = Object.fromEntries(c.criteria.map((x: any) => [x.id, x])); return <tr key={c.id}><td>{c.status === "analyzed" ? <Link to={`/app/recruitment/candidate/${c.id}`}>{c.filename}</Link> : c.filename}{c.error && <div className="field-err">{c.error}</div>}</td><td><Badge s={c.status} /></td>
            <td>{c.overall ?? "—"}</td><td>{c.coverage != null ? c.coverage + "%" : "—"}</td>{proj.criteria.map((k: any) => <td key={k.id} title={by[k.id]?.explanation}>{by[k.id] ? <Badge s={by[k.id].status} /> : "—"}</td>)}</tr>; })}
        </tbody></table></div>
        <div className="row"><button className="btn small ghost" onClick={() => exportIt("csv")}>Export CSV</button><button className="btn small ghost" onClick={() => exportIt("docx")}>Export Word</button></div></div>}
      {analyzed.length > 0 && <Charts res={res} analyzed={analyzed} />}
    </div>
  );
}

function Table({ rows, cols }: { rows: any[]; cols: string[] }) {
  return <details><summary className="muted small">Show data as a table</summary><div className="table-wrap"><table><thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead><tbody>{rows.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c}>{r[c] ?? "missing"}</td>)}</tr>)}</tbody></table></div></details>;
}

function Charts({ res, analyzed }: { res: any; analyzed: any[] }) {
  const crit = res.project.criteria;
  const bar = analyzed.map((c) => ({ Candidate: c.filename, "Match score": c.overall ?? undefined, "Evidence coverage": c.coverage ?? undefined }));
  const cov = analyzed.map((c) => ({ Candidate: c.filename, Supported: c.criteria.filter((x: any) => ["supported_by_work_sample", "listed_in_cv"].includes(x.status)).length, Partial: c.criteria.filter((x: any) => x.status === "partial").length, "Not found": c.criteria.filter((x: any) => x.status === "not_found").length, "Unable to verify": c.criteria.filter((x: any) => x.status === "unable_to_verify").length }));
  const port = analyzed.map((c) => { const repos = c.portfolio.flatMap((p: any) => p.repo_details || []); return { Candidate: c.filename, "Repos inspected": repos.length, "With README": repos.filter((r: any) => r.has_readme).length, "With tests": repos.filter((r: any) => r.has_tests).length, "With docs folder": repos.filter((r: any) => r.has_docs).length }; });
  const sel = analyzed.slice(0, 3);
  const shared = crit.filter((k: any) => sel.every((c) => c.criteria.find((x: any) => x.id === k.id)?.value != null));
  const radar = shared.map((k: any) => ({ criterion: k.name, ...Object.fromEntries(sel.map((c) => [c.filename, Math.round((c.criteria.find((x: any) => x.id === k.id).value) * 100)])) }));
  const matrix = crit.map((k: any) => ({ Criterion: k.name, ...Object.fromEntries(analyzed.map((c) => [c.filename, STATUS_LABEL[c.criteria.find((x: any) => x.id === k.id)?.status] ?? "missing"])) }));
  return (
    <div className="card"><h3>Charts (computed from stored results)</h3>
      <p className="muted small">Score = job-requirement match, not a measure of a person. Missing evidence is shown as missing, never as a low ability score.</p>
      <h4>Candidate match score and evidence coverage</h4><div className="chart"><ResponsiveContainer><BarChart data={bar}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="Candidate" /><YAxis domain={[0, 100]} /><Tooltip /><Legend /><Bar dataKey="Match score" fill={COLORS[0]} /><Bar dataKey="Evidence coverage" fill={COLORS[1]} /></BarChart></ResponsiveContainer></div><Table rows={bar} cols={["Candidate", "Match score", "Evidence coverage"]} />
      <h4>Skill and criterion matrix</h4><Table rows={matrix} cols={["Criterion", ...analyzed.map((c) => c.filename)]} />
      <h4>Evidence coverage by status (number of criteria)</h4><div className="chart"><ResponsiveContainer><BarChart data={cov}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="Candidate" /><YAxis allowDecimals={false} /><Tooltip /><Legend />{["Supported", "Partial", "Not found", "Unable to verify"].map((k, i) => <Bar key={k} dataKey={k} stackId="a" fill={["#0f766e", "#d97706", "#9ca3af", "#6366f1"][i]} />)}</BarChart></ResponsiveContainer></div><Table rows={cov} cols={["Candidate", "Supported", "Partial", "Not found", "Unable to verify"]} />
      <h4>Radar: criteria with evidence for all of the first {sel.length} candidates</h4>
      {sel.length >= 1 && radar.length >= 3 && radar.length <= 8 ? <div className="chart"><ResponsiveContainer><RadarChart data={radar}><PolarGrid /><PolarAngleAxis dataKey="criterion" /><PolarRadiusAxis domain={[0, 100]} />{sel.map((c, i) => <Radar key={c.id} name={c.filename} dataKey={c.filename} stroke={COLORS[i]} fill={COLORS[i]} fillOpacity={0.25} />)}<Legend /><Tooltip /></RadarChart></ResponsiveContainer></div> : <p className="muted">The radar needs 3–8 criteria that have evidence for every selected candidate; use the table instead.</p>}
      {radar.length > 0 && <Table rows={radar} cols={["criterion", ...sel.map((c) => c.filename)]} />}
      <h4>Observed repository evidence (counts, not quality scores)</h4><div className="chart"><ResponsiveContainer><BarChart data={port}><CartesianGrid strokeDasharray="3 3" /><XAxis dataKey="Candidate" /><YAxis allowDecimals={false} /><Tooltip /><Legend />{["Repos inspected", "With README", "With tests", "With docs folder"].map((k, i) => <Bar key={k} dataKey={k} fill={COLORS[i]} />)}</BarChart></ResponsiveContainer></div><Table rows={port} cols={["Candidate", "Repos inspected", "With README", "With tests", "With docs folder"]} />
    </div>
  );
}

export function Candidate() {
  const id = Number(useParams().id); const [r, setR] = useState<any>(null); const [err, setErr] = useState("");
  useEffect(() => { api(`/recruitment/candidates/${id}/report`).then(setR).catch((e) => setErr(errMsg(e))); }, [id]);
  if (err) return <Alert>{err}</Alert>; if (!r) return <Skeleton h={200} />;
  const Crit = ({ x }: { x: any }) => <div className="card"><div className="row between"><b>{x.name}</b><Badge s={x.status} /></div><p className="muted small">Weight {x.weight} · {x.level}</p><p>{x.explanation}</p>
    {x.evidence.map((e: any, i: number) => <blockquote key={i}><span className="muted small">{e.source_type} · {e.location} · verification: {e.verification}{e.caveat ? ` · ${e.caveat}` : ""}</span><br />{e.excerpt}</blockquote>)}</div>;
  return (
    <div><Link to={-1 as any}>← Back</Link><h1>Candidate report</h1><p className="muted">{r.overview.filename} · evaluated {r.evaluated_at ? new Date(r.evaluated_at).toLocaleString() : ""}</p>
      <Alert kind="info">{r.limitations[0]}</Alert>
      <div className="grid3"><div className="card stat"><div className="muted">Job-requirement match</div><div className="big">{r.overall ?? "—"}</div></div><div className="card stat"><div className="muted">Evidence coverage</div><div className="big">{r.coverage ?? "—"}%</div></div><div className="card stat"><div className="muted">Role</div><div>{r.job.title}</div></div></div>
      <details><summary className="muted">How the score is calculated</summary><p className="small">{r.formula}</p></details>
      <h3>Matched requirements</h3>{r.matched.length ? r.matched.map((x: any) => <Crit key={x.id} x={x} />) : <p className="muted">None.</p>}
      {r.partial.length > 0 && <><h3>Partially supported</h3>{r.partial.map((x: any) => <Crit key={x.id} x={x} />)}</>}
      <h3>Missing or uncertain evidence</h3>{r.missing_or_uncertain.length ? r.missing_or_uncertain.map((x: any) => <Crit key={x.id} x={x} />) : <p className="muted">None.</p>}
      <h3>Portfolio and repository findings</h3>{r.portfolio.length ? r.portfolio.map((p: any, i: number) => <div className="card" key={i}><b>{p.url}</b> <Badge s={p.status} />{p.reason && <p className="muted small">{p.reason}</p>}
        {p.repos.map((x: any) => <p key={x.name} className="small"><b>{x.name}</b> {x.fork && "(fork) "}· README: {x.has_readme ? "yes" : "no"} · tests: {x.has_tests ? "found" : "not found"} · docs: {x.has_docs ? "found" : "not found"} · languages: {Object.entries(x.languages || {}).map(([k, v]) => `${k} ${v}%`).join(", ") || "n/a"}</p>)}
        {p.notes?.map((n: string) => <p className="muted small" key={n}>{n}</p>)}{p.retrieved_at && <p className="muted small">Retrieved {new Date(p.retrieved_at).toLocaleString()}</p>}</div>) : <p className="muted">No portfolio links found in the CV.</p>}
      <h3>Suggested interview questions</h3><p className="muted small">These structure verification at interview; they do not prove ability.</p>
      {r.interview_questions.map((q: any, i: number) => <div className="card" key={i}><b>{q.question}</b><p className="muted small">Skill: {q.skill} · {q.why}{q.evidence_ref ? ` · Evidence: ${q.evidence_ref}` : ""}</p><ul>{q.rubric.map((x: string) => <li key={x}>{x}</li>)}</ul></div>)}
      <h3>Limitations</h3><ul>{r.limitations.map((l: string) => <li key={l}>{l}</li>)}</ul>
    </div>
  );
}
