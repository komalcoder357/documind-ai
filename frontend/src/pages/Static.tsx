import { Link } from "react-router-dom";
import HeroScene from "../components/HeroScene";
import Doci from "../components/Doci";

export function Landing() {
  return (
    <main>
      <section className="hero">
        <div><p className="eyebrow">Document intelligence · Recruitment intelligence</p>
          <h1>Answers you can trace back to the page.</h1>
          <p className="lead">DocuMind AI reads your PDFs, Word files and CVs, then answers with citations, compares documents, and explains every candidate score with evidence. It tells you when evidence is missing instead of guessing.</p>
          <div className="row"><Link className="btn" to="/register">Get started</Link><Link className="btn ghost" to="/features">How it works</Link></div></div>
        <HeroScene />
      </section>
      <section className="grid3 pad">
        {[["Evidence-grounded Q&A", "Hybrid BM25 + vector retrieval with page-level citations that are validated against stored passages."], ["Explainable CV analysis", "Configurable criteria and weights, criterion-level evidence, GitHub checks through the official API, and honest 'not verified' states."], ["Private by design", "Workspace isolation, server-side authorization, and deletion of files and indexed data on request."]].map(([t, d]) => <div className="card" key={t}><h3>{t}</h3><p className="muted">{d}</p></div>)}
      </section>
    </main>
  );
}
const Page = ({ title, children }: { title: string; children: React.ReactNode }) => <main className="narrow pad"><div className="center"><Doci state="idle" size={64} /></div><h1>{title}</h1>{children}</main>;
export const Features = () => <Page title="Features and workflow"><ol className="steps"><li><b>Upload</b> PDF, DOCX or TXT. Files are validated by content, not just extension.</li><li><b>Process</b> Text is extracted page by page, split into chunks and indexed. Status is real and persisted.</li><li><b>Ask</b> Hybrid retrieval finds passages; answers cite document, page and excerpt.</li><li><b>Compare</b> Find shared themes and possible conflicts (flagged for human review).</li><li><b>Recruit</b> Define criteria, upload CVs, inspect evidence, compare candidates, export reports.</li></ol><p className="muted">Without a configured language model, answers are shown as extracted passages (extractive mode) and labelled as such.</p></Page>;
export const Privacy = () => <Page title="Privacy policy"><p>We store your account details, uploaded files, extracted text and analysis results so the service works for you. Data is isolated per workspace. You can delete any document, project or your whole account; this removes files, chunks, embeddings and dependent records.</p><p>If an external language model provider is configured by the operator, only the minimum retrieved passages are sent to it. Your documents are not used to train models by this application. Operators must complete their own retention and legal review before production use.</p></Page>;
export const Terms = () => <Page title="Terms of use"><p>Use DocuMind AI lawfully and only with documents you are allowed to process. Recruitment results are decision support, not decisions: a human must review them, and protected characteristics must never be used to rank people. Outputs may contain errors; verify important findings against the original sources.</p></Page>;
export const Contact = () => <Page title="Contact and support"><p>Operators should set a support address here before deployment. Include the document or job ID shown in the app when reporting a problem; never send passwords.</p></Page>;
export const NotFound = () => <Page title="Page not found"><p><Link to="/">Return home</Link></p></Page>;
