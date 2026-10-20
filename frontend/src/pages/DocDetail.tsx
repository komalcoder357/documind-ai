
import { FormEvent, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { api, errMsg } from "../api";
import Doci, { DociState } from "../components/Doci";
import { Alert, Skeleton } from "../components/ui";

type Cite = {
  n: number;
  document_title: string;
  page: number | null;
  excerpt: string;
  document_id: number;
  heading?: string;
};

type ChatEntry = {
  question: string;
  r: {
    conversation_id?: number;
    answer: string;
    insufficient?: boolean;
    mode?: string;
    warnings?: string[];
    citations?: Cite[];
    citation_status?: string;
    pipeline?: unknown;
  };
};

export default function DocDetail() {
  const id = Number(useParams().id);
  const [doc, setDoc] = useState<any>(null);
  const [tab, setTab] = useState<"ask" | "summary" | "text">("ask");
  const [err, setErr] = useState("");

  useEffect(() => {
    let active = true;
    setDoc(null);
    setErr("");

    api(`/documents/${id}`)
      .then((data) => {
        if (active) setDoc(data);
      })
      .catch((e) => {
        if (active) setErr(errMsg(e));
      });

    return () => {
      active = false;
    };
  }, [id]);

  if (err) return <Alert>{err}</Alert>;
  if (!doc) return <Skeleton h={200} />;

  return (
    <div>
      <h1>{doc.title}</h1>

      <p className="muted">
        {doc.kind.toUpperCase()}
        {doc.page_count ? ` · ${doc.page_count} pages` : ""}
        {" · "}
        <a
          href={`/api/v1/documents/${id}/file`}
          target="_blank"
          rel="noreferrer"
        >
          Open original file
        </a>
      </p>

      {doc.warnings?.map((w: string) => (
        <Alert kind="info" key={w}>{w}</Alert>
      ))}

      <div className="tabs" role="tablist">
        {(["ask", "summary", "text"] as const).map((t) => (
          <button
            key={t}
            role="tab"
            aria-selected={tab === t}
            className={tab === t ? "on" : ""}
            onClick={() => setTab(t)}
          >
            {t === "ask"
              ? "Ask questions"
              : t === "summary"
                ? "Summary"
                : "Extracted text"}
          </button>
        ))}
      </div>

      {tab === "ask" && <Ask id={id} kind={doc.kind} />}
      {tab === "summary" && <Summary id={id} />}
      {tab === "text" && <pre className="card text">{doc.text}</pre>}
    </div>
  );
}

function Ask({ id, kind }: { id: number; kind: string }) {
  const storageKey = `documind:chat:${id}`;

  const [q, setQ] = useState("");
  const [conv, setConv] = useState<number | null>(null);
  const [log, setLog] = useState<ChatEntry[]>([]);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const [d, setD] = useState<DociState>("idle");

  useEffect(() => {
    try {
      const saved = localStorage.getItem(storageKey);

      if (!saved) {
        setConv(null);
        setLog([]);
        setD("idle");
        return;
      }

      const parsed = JSON.parse(saved);
      const restoredLog: ChatEntry[] = Array.isArray(parsed.log)
        ? parsed.log
        : [];

      setConv(
        typeof parsed.conv === "number" ? parsed.conv : null
      );
      setLog(restoredLog);

      if (restoredLog.length > 0) {
        setD("evidence");
      } else {
        setD("idle");
      }
    } catch {
      setConv(null);
      setLog([]);
      setD("idle");
    }
  }, [storageKey]);

  async function submit(e: FormEvent) {
    e.preventDefault();

    const question = q.trim();
    if (question.length < 3 || busy) return;

    setBusy(true);
    setErr("");
    setD("thinking");

    try {
      const r = await api(`/documents/${id}/questions`, {
        body: {
          question,
          conversation_id: conv,
        },
      });

      const nextConv: number | null =
        typeof r.conversation_id === "number"
          ? r.conversation_id
          : conv;

      const nextLog: ChatEntry[] = [
        ...log,
        { question, r },
      ];

      localStorage.setItem(
        storageKey,
        JSON.stringify({
          conv: nextConv,
          log: nextLog,
        })
      );

      setConv(nextConv);
      setLog(nextLog);
      setQ("");
      setD(r.insufficient ? "insufficient" : "evidence");
    } catch (x) {
      setErr(errMsg(x));
      setD("concerned");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div>
      <div className="center">
        <Doci state={d} size={64} />
      </div>

      {log.map((m, i) => (
        <div className="card" key={i}>
          <p>
            <b>You:</b> {m.question}
          </p>

          {m.r.insufficient ? (
            <Alert kind="info">{m.r.answer}</Alert>
          ) : (
            <div>
              <p className="pre">
                <b>DocuMind:</b> {m.r.answer}
              </p>

              {m.r.mode === "extractive_fallback" && (
                <p className="muted small">
                  Extractive mode: the language model was unavailable,
                  so these are retrieved passages rather than a
                  generated answer.
                </p>
              )}

              {(m.r.warnings ?? []).map((w, j) => (
                <Alert kind="info" key={`${i}-${j}`}>
                  {w}
                </Alert>
              ))}

              <h4>
                Sources{" "}
                <span className="muted small">
                  (citation check: {m.r.citation_status ?? "unknown"})
                </span>
              </h4>

              {(m.r.citations ?? []).map((c) => (
                <blockquote key={`${c.n}-${c.document_id}`}>
                  <b>
                    [{c.n}] {c.document_title}
                    {c.page ? `, page ${c.page}` : ""}
                  </b>

                  {c.heading ? (
                    <span className="muted"> · {c.heading}</span>
                  ) : null}

                  <br />
                  {c.excerpt}

                  {kind === "pdf" && c.page && (
                    <div>
                      <a
                        href={`/api/v1/documents/${c.document_id}/file#page=${c.page}`}
                        target="_blank"
                        rel="noreferrer"
                      >
                        Open page {c.page}
                      </a>
                    </div>
                  )}
                </blockquote>
              ))}

              {m.r.pipeline != null && (
                <details>
                  <summary className="muted small">
                    Retrieval pipeline used
                  </summary>
                  <pre className="small">
                    {JSON.stringify(m.r.pipeline, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          )}
        </div>
      ))}

      {err && <Alert>{err}</Alert>}

      <form onSubmit={submit} className="row">
        <input
          aria-label="Your question"
          className="grow"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          placeholder="Ask about this document…"
          maxLength={1000}
        />

        <button
          className="btn"
          disabled={busy || q.trim().length < 3}
        >
          {busy ? "Searching…" : "Ask"}
        </button>
      </form>
    </div>
  );
}

function Summary({ id }: { id: number }) {
  const [s, setS] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);

  async function run() {
    setBusy(true);
    setErr("");

    try {
      setS(await api(`/documents/${id}/summary`, { method: "POST" }));
    } catch (e) {
      setErr(errMsg(e));
    } finally {
      setBusy(false);
    }
  }

  const List = ({ items }: { items: any[] }) => (
    <ul>
      {(items ?? []).map((x, i) => (
        <li key={i}>
          {x.text}
          {x.page ? (
            <span className="muted"> (p. {x.page})</span>
          ) : null}
        </li>
      ))}
    </ul>
  );

  return (
    <div className="card">
      <button className="btn" onClick={run} disabled={busy}>
        {busy ? "Working…" : "Generate summary"}
      </button>

      {err && <Alert>{err}</Alert>}

      {s && (
        <div>
          <Alert kind="info">{s.note}</Alert>

          <h3>Overview</h3>
          <List items={s.overview} />

          <h3>Key findings</h3>
          <List items={s.key_findings} />

          <h3>Key terms</h3>
          <p>{(s.key_terms ?? []).join(", ")}</p>

          <h3>Entities</h3>
          <p>{(s.entities ?? []).join(", ") || "None detected"}</p>

          <h3>Dates</h3>
          <p>{(s.dates ?? []).join(", ") || "None detected"}</p>

          <h3>Limitations stated by the source</h3>
          {(s.stated_limitations ?? []).length ? (
            <List items={s.stated_limitations} />
          ) : (
            <p className="muted">None found.</p>
          )}
        </div>
      )}
    </div>
  );
}
