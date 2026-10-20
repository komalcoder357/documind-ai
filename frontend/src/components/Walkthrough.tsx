import { useState } from "react";
import Doci from "./Doci";
export const STEPS = [
  { t: "Upload documents", d: "Add PDF, DOCX or TXT files in Documents. You need the file; processing starts automatically. If it fails, the error explains why and you can retry." },
  { t: "Understand processing", d: "Each upload shows a real stage (extracting, chunking, embedding, indexing). Status is stored on the server, so you can leave and come back." },
  { t: "Ask questions", d: "Open a ready document and ask in plain language. You get passages from your documents, not invented facts." },
  { t: "Read citations", d: "Every citation shows the document, page and excerpt, and links to the original file. If evidence is missing, Doci says so instead of guessing." },
  { t: "Create a recruitment project", d: "Describe the role and list required and preferred skills. Criteria are saved before any CV is analyzed." },
  { t: "Configure criteria", d: "Edit skills, experience, education and weights. The score formula is shown, and nothing uses names or personal traits." },
  { t: "Review candidate evidence", d: "Upload CVs, run the analysis, then open a candidate to see per-criterion evidence, portfolio checks and what could not be verified." },
  { t: "Compare and export", d: "Use the charts and table to compare candidates, then export CSV or Word. Results support, and never replace, human review." },
];
export default function Walkthrough({ onClose }: { onClose: (done: boolean) => void }) {
  const [i, setI] = useState(0); const s = STEPS[i];
  return (
    <div className="modal-bg" role="dialog" aria-modal="true" aria-labelledby="wt-title">
      <div className="modal glass">
        <Doci state="greeting" size={64} />
        <p className="muted">Step {i + 1} of {STEPS.length}</p>
        <h2 id="wt-title">{s.t}</h2><p>{s.d}</p>
        <div className="row">
          <button className="btn ghost" onClick={() => setI(Math.max(0, i - 1))} disabled={i === 0}>Back</button>
          {i < STEPS.length - 1 ? <button className="btn" onClick={() => setI(i + 1)}>Next</button> : <button className="btn" onClick={() => onClose(true)}>Finish</button>}
          <button className="btn ghost" onClick={() => setI(0)}>Restart</button>
          <button className="btn ghost" onClick={() => onClose(true)}>Skip</button>
        </div>
      </div>
    </div>
  );
}
