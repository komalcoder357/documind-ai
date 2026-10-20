import { useEffect, useState } from "react";
import { BrowserRouter, Link, NavLink, Navigate, Outlet, Route, Routes, useNavigate } from "react-router-dom";
import { api } from "./api";
import { AuthProvider, useAuth } from "./auth";
import Doci from "./components/Doci";
import Walkthrough from "./components/Walkthrough";
import { Skeleton } from "./components/ui";
import { Forgot, Login, Register, Reset } from "./pages/Auth";
import { Landing, Features, Privacy, Terms, Contact, NotFound } from "./pages/Static";
import Dashboard from "./pages/Dashboard";
import Documents from "./pages/Documents";
import DocDetail from "./pages/DocDetail";
import Compare from "./pages/Compare";
import { Projects, Project, Candidate } from "./pages/Recruitment";
import { Reports, Settings, Admin } from "./pages/Misc";

function PublicLayout() {
  const { user } = useAuth();
  return <><header className="top glass"><Link to="/" className="brand"><Doci size={28} /> DocuMind AI</Link><nav><Link to="/features">Features</Link><Link to="/privacy">Privacy</Link>{user ? <Link className="btn small" to="/app">Open app</Link> : <><Link to="/login">Sign in</Link><Link className="btn small" to="/register">Get started</Link></>}</nav></header><Outlet />
    <footer className="muted center pad small"><Link to="/terms">Terms</Link> · <Link to="/privacy">Privacy</Link> · <Link to="/contact">Contact</Link></footer></>;
}

function Private() {
  const { user, loading, setUser } = useAuth(); const nav = useNavigate(); const [tour, setTour] = useState(false);
  useEffect(() => { if (user && !user.prefs?.onboarding_done) setTour(true); }, [user]);
  useEffect(() => { const f = () => setTour(true); window.addEventListener("replay-tour", f); return () => window.removeEventListener("replay-tour", f); }, []);
  if (loading) return <div className="pad"><Skeleton h={200} /></div>;
  if (!user) return <Navigate to="/login" replace />;
  async function closeTour(done: boolean) { setTour(false); if (done) try { setUser(await api("/me/preferences", { method: "PUT", body: { onboarding_done: true } })); } catch { /* non-critical */ } }
  async function logout() { try { await api("/auth/logout", { method: "POST" }); } catch { /* ignore */ } setUser(null); nav("/"); }
  const links: [string, string][] = [["/app", "Dashboard"], ["/app/documents", "Documents"], ["/app/compare", "Compare"], ["/app/recruitment", "Recruitment"], ["/app/reports", "Reports"], ["/app/settings", "Settings"]];
  if (user.role === "admin") links.push(["/app/admin", "Admin"]);
  return <div className="shell"><aside className="side glass"><Link to="/" className="brand"><Doci size={28} /> DocuMind</Link><nav aria-label="Main">{links.map(([to, t]) => <NavLink key={to} to={to} end={to === "/app"}>{t}</NavLink>)}</nav>
    <div className="side-foot"><div className="muted small">{user.full_name}</div><button className="btn ghost small" onClick={() => setTour(true)}>Guide</button> <button className="btn ghost small" onClick={logout}>Log out</button></div></aside>
    <main className="content"><Outlet context={{ replay: () => setTour(true) }} /></main>{tour && <Walkthrough onClose={closeTour} />}</div>;
}

function AdminGuard({ children }: { children: JSX.Element }) { const { user } = useAuth(); return user?.role === "admin" ? children : <Navigate to="/app" replace />; }
function SettingsPage() { return <Settings replay={() => window.dispatchEvent(new Event("replay-tour"))} />; }

export default function App() {
  return <AuthProvider><BrowserRouter><Routes>
    <Route element={<PublicLayout />}><Route path="/" element={<Landing />} /><Route path="/features" element={<Features />} /><Route path="/privacy" element={<Privacy />} /><Route path="/terms" element={<Terms />} /><Route path="/contact" element={<Contact />} />
      <Route path="/login" element={<Login />} /><Route path="/register" element={<Register />} /><Route path="/forgot" element={<Forgot />} /><Route path="/reset" element={<Reset />} /></Route>
    <Route path="/app" element={<Private />}><Route index element={<Dashboard />} /><Route path="documents" element={<Documents />} /><Route path="documents/:id" element={<DocDetail />} /><Route path="compare" element={<Compare />} />
      <Route path="recruitment" element={<Projects />} /><Route path="recruitment/candidate/:id" element={<Candidate />} /><Route path="recruitment/:id" element={<Project />} /><Route path="reports" element={<Reports />} />
      <Route path="settings" element={<SettingsPage />} /><Route path="admin" element={<AdminGuard><Admin /></AdminGuard>} /></Route>
    <Route path="*" element={<NotFound />} /></Routes></BrowserRouter></AuthProvider>;
}
