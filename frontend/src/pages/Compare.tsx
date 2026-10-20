import { useEffect, useState } from "react";
import { api, errMsg } from "../api";
import { Alert, Empty } from "../components/ui";
import Doci from "../components/Doci";

export default function Compare() {
  const [docs, setDocs] = useState<any[]>([]); const [sel, setSel] = useState<number[]>([]); const [cmp, setCmp] = useState<any>(null); const [res, setRes] = useState<any>(null); const [err, setErr] = useState(""); const [busy, setBusy] = useState(false); const [saved, setSaved] = useState("");
  useEffect(() => { api("/documents").then((d) => setDocs(d.filter((x: any) => x.status === "ready"))).catch((e) => setErr(errMsg(e))); }, []);
  const toggle = (id: number) => setSel((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]));
  async function go(kind: "compare" | "research") {
    setBusy(true); setErr(""); setCmp(null); setRes(null); setSaved("");
    try { if (kind === "compare") setCmp(await api("/documents/compare", { body: { doc_ids: sel } })); else setRes(await api("/research/analyze", { body: { doc_ids: sel } })); } catch (e) { setErr(errMsg(e)); } setBusy(false);
  }
  async function save(kind: string, payload: any) { try { await api("/reports", { body: { title: `${kind} (${new Date().toLocaleDateString()})`, kind, payload } }); setSaved("Saved to Reports."); } catch (e) { setErr(errMsg(e)); } }
  if (!docs.length && !err) return <Empty title="No ready documents">Upload and process at least two documents to compare them.</Empty>;
  const Src = ({ s }: { s: any }) => <div className="src"><b>{s.document}</b>{s.page ? `, p.${s.page}` : ""}<br />“{s.text}”</div>;
  return (
    <div><h1>Compare and research</h1>
      <div className="card"><h3>Select documents (2–5)</h3>{docs.map((d) => <label key={d.id} className="check"><input type="checkbox" checked={sel.includes(d.id)} onChange={() => toggle(d.id)} /> {d.title}</label>)}
        <div className="row"><button className="btn" disabled={sel.length < 2 || sel.length > 5 || busy} onClick={() => go("compare")}>Compare & find conflicts</button><button className="btn ghost" disabled={!sel.length || busy} onClick={() => go("research")}>Analyze as research papers</button></div></div>
      {err && <Alert>{err}</Alert>}{saved && <Alert kind="ok">{saved}</Alert>}
      {cmp && <div className="card"><div className="row between"><h3>Comparison</h3><button className="btn small ghost" onClick={() => save("document_comparison", cmp)}>Save report</button></div><p className="muted small">Method: {cmp.method}</p>
        <p><b>Common terms:</b> {cmp.common_terms.join(", ") || "none"}</p>{Object.entries(cmp.distinct_terms).map(([k, v]: any) => <p key={k}><b>Distinct in {k}:</b> {v.join(", ")}</p>)}
        <h3>Possible conflicts ({cmp.possible_conflicts.length})</h3>{cmp.possible_conflicts.length === 0 && <p className="muted">No candidate conflicts were flagged. This does not prove the documents agree.</p>}
        {cmp.possible_conflicts.map((c: any, i: number) => <div className="conflict" key={i}><Src s={c.statement_a} /><Src s={c.statement_b} /><p className="muted small">Flagged because: {c.why_flagged}. {c.caution} <b>Status: needs human review.</b></p></div>)}</div>}
      {res && <div className="card"><div className="row between"><h3>Research analysis</h3><button className="btn small ghost" onClick={() => save("research_analysis", res)}>Save report</button></div>
        {res.papers.map((p: any) => <div key={p.document_id}><h4>{p.title}</h4>{Object.entries(p.sections).filter(([, v]: any) => v.length).map(([k, v]: any) => <p key={k}><b>{k.replace("_", " ")}:</b> {v[0].excerpt} <span className="muted">(p.{v[0].page ?? "–"})</span></p>)}
          {p.metrics.length > 0 && <p><b>Metrics found:</b> {p.metrics.map((m: any) => `${m.metric} ${m.value}`).join("; ")}</p>}<p className="muted small">Not found: {p.not_found.join(", ") || "none"}. {p.note}</p></div>)}
        <h4>Research gaps</h4><p className="muted small">{res.gap_analysis.note}</p>
        <p><b>1. Limitations stated by authors:</b> {Object.values(res.gap_analysis["1_limitations_stated_by_authors"]).flat().length || "none found"}</p>
        <p><b>2. Differences across papers:</b> {res.gap_analysis["2_differences_across_papers"].length}</p><p><b>3. AI hypotheses:</b> none (needs a configured LLM)</p></div>}
      <div className="center"><Doci state={cmp || res ? "comparing" : "idle"} size={56} /></div>
    </div>
  );
}
