import { ReactNode } from "react";
import Doci, { DociState } from "./Doci";
export const Alert = ({ kind = "error", children }: { kind?: "error" | "ok" | "info"; children: ReactNode }) => <div role={kind === "error" ? "alert" : "status"} className={`alert ${kind}`}>{children}</div>;
export const Skeleton = ({ h = 20 }: { h?: number }) => <div className="skeleton" style={{ height: h }} aria-hidden />;
export const Empty = ({ state = "empty", title, children }: { state?: DociState; title: string; children?: ReactNode }) =>
  <div className="empty"><Doci state={state} size={72} /><h3>{title}</h3><div className="muted">{children}</div></div>;
export const Badge = ({ s }: { s: string }) => <span className={`badge b-${s}`}>{s.replace(/_/g, " ")}</span>;
export const fmtBytes = (n: number) => n > 1e6 ? (n / 1e6).toFixed(1) + " MB" : n > 1e3 ? (n / 1e3).toFixed(1) + " KB" : n + " B";
