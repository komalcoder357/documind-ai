import { FormEvent, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { api, errMsg } from "../api";
import { useAuth } from "../auth";
import Doci, { DociState } from "../components/Doci";
import { Alert } from "../components/ui";

function Shell({ title, doci, children }: { title: string; doci: DociState; children: React.ReactNode }) {
  return <main className="auth"><div className="card auth-card"><div className="center"><Doci state={doci} size={84} /></div><h1>{title}</h1>{children}</div></main>;
}

export function Login() {
  const nav = useNavigate(); const { setUser } = useAuth();
  const [email, setEmail] = useState(""); const [pw, setPw] = useState(""); const [err, setErr] = useState(""); const [d, setD] = useState<DociState>("greeting"); const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault(); setErr(""); setBusy(true); setD("thinking");
    try { const u = await api("/auth/login", { body: { email, password: pw } }); setD("success"); setUser(u); setTimeout(() => nav("/app"), 500); }
    catch (x) { setErr(errMsg(x)); setD("concerned"); setBusy(false); }
  }
  return (
    <Shell title="Welcome back" doci={d}>
      <form onSubmit={submit} noValidate>
        {err && <Alert>{err}</Alert>}
        <label>Email<input type="email" autoComplete="email" value={email} onFocus={() => setD("focus-email")} onBlur={() => setD(err ? "concerned" : "idle")} onChange={(e) => { setEmail(e.target.value); setErr(""); }} required /></label>
        <label>Password<input type="password" autoComplete="current-password" value={pw} onFocus={() => setD("focus-password")} onBlur={() => setD(err ? "concerned" : "idle")} onChange={(e) => { setPw(e.target.value); setErr(""); }} required /></label>
        <button className="btn block" disabled={busy || !email || !pw}>{busy ? "Signing in…" : "Sign in"}</button>
      </form>
      <p className="muted center"><Link to="/forgot">Forgot password?</Link> · <Link to="/register">Create account</Link></p>
    </Shell>
  );
}

export function Register() {
  const nav = useNavigate(); const { setUser } = useAuth();
  const [f, setF] = useState({ full_name: "", email: "", password: "", confirm: "", accept_terms: false }); const [err, setErr] = useState(""); const [d, setD] = useState<DociState>("greeting");
  const problems = [f.password && f.password.length < 8 && "Password must be at least 8 characters.", f.confirm && f.confirm !== f.password && "Passwords do not match."].filter(Boolean) as string[];
  const set = (k: string) => (e: any) => setF({ ...f, [k]: e.target.type === "checkbox" ? e.target.checked : e.target.value });
  async function submit(e: FormEvent) {
    e.preventDefault(); setErr(""); setD("thinking");
    try {
      await api("/auth/register", { body: { full_name: f.full_name, email: f.email, password: f.password, accept_terms: f.accept_terms } });
      setUser(await api("/auth/login", { body: { email: f.email, password: f.password } })); setD("success"); setTimeout(() => nav("/app"), 600);
    } catch (x) { setErr(errMsg(x)); setD("concerned"); }
  }
  return (
    <Shell title="Create your account" doci={problems.length || err ? "concerned" : d}>
      <form onSubmit={submit} noValidate>
        {err && <Alert>{err}</Alert>}
        <label>Full name<input value={f.full_name} onChange={set("full_name")} required autoComplete="name" /></label>
        <label>Email<input type="email" value={f.email} onChange={set("email")} required autoComplete="email" onFocus={() => setD("focus-email")} /></label>
        <label>Password<input type="password" value={f.password} onChange={set("password")} required autoComplete="new-password" onFocus={() => setD("focus-password")} /></label>
        <label>Confirm password<input type="password" value={f.confirm} onChange={set("confirm")} required autoComplete="new-password" onFocus={() => setD("focus-password")} /></label>
        {problems.map((p) => <p key={p} className="field-err" role="alert">{p}</p>)}
        <label className="check"><input type="checkbox" checked={f.accept_terms} onChange={set("accept_terms")} /> I accept the <Link to="/terms">Terms of Use</Link> and <Link to="/privacy">Privacy Policy</Link></label>
        <button className="btn block" disabled={!f.full_name || !f.email || f.password.length < 8 || f.password !== f.confirm || !f.accept_terms}>Create account</button>
      </form>
      <p className="muted center">Already registered? <Link to="/login">Sign in</Link></p>
    </Shell>
  );
}

export function Forgot() {
  const [email, setEmail] = useState(""); const [msg, setMsg] = useState(""); const [err, setErr] = useState(""); const [tok, setTok] = useState("");
  async function submit(e: FormEvent) { e.preventDefault(); setErr(""); try { const r = await api("/auth/forgot-password", { body: { email } }); setMsg(r.message); setTok(r.dev_token || ""); } catch (x) { setErr(errMsg(x)); } }
  return (
    <Shell title="Reset your password" doci="idle">
      <form onSubmit={submit}>
        {err && <Alert>{err}</Alert>}{msg && <Alert kind="ok">{msg}</Alert>}
        {tok && <Alert kind="info">Development mode: <Link to={`/reset?token=${tok}`}>open reset link</Link></Alert>}
        <label>Email<input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required /></label>
        <button className="btn block" disabled={!email}>Send reset link</button>
      </form>
      <p className="muted center"><Link to="/login">Back to sign in</Link></p>
    </Shell>
  );
}

export function Reset() {
  const [q] = useSearchParams(); const nav = useNavigate(); const [pw, setPw] = useState(""); const [err, setErr] = useState(""); const [ok, setOk] = useState(false);
  async function submit(e: FormEvent) { e.preventDefault(); setErr(""); try { await api("/auth/reset-password", { body: { token: q.get("token") || "", password: pw } }); setOk(true); setTimeout(() => nav("/login"), 1200); } catch (x) { setErr(errMsg(x)); } }
  return (
    <Shell title="Choose a new password" doci={ok ? "success" : err ? "concerned" : "idle"}>
      <form onSubmit={submit}>{err && <Alert>{err}</Alert>}{ok && <Alert kind="ok">Password updated. Redirecting to sign in…</Alert>}
        <label>New password<input type="password" value={pw} onChange={(e) => setPw(e.target.value)} minLength={8} required autoComplete="new-password" /></label>
        <button className="btn block" disabled={pw.length < 8}>Update password</button></form>
    </Shell>
  );
}
