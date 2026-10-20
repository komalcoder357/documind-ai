import { createContext, useContext, useEffect, useState, ReactNode } from "react";
import { api } from "./api";
export type User = { id: number; email: string; full_name: string; role: string; prefs: Record<string, any> };
type Ctx = { user: User | null; loading: boolean; setUser: (u: User | null) => void; refresh: () => Promise<void> };
const C = createContext<Ctx>({ user: null, loading: true, setUser: () => {}, refresh: async () => {} });
export const useAuth = () => useContext(C);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null); const [loading, setLoading] = useState(true);
  const refresh = async () => { try { setUser(await api("/auth/me")); } catch { setUser(null); } setLoading(false); };
  useEffect(() => { refresh(); }, []);
  useEffect(() => { document.documentElement.dataset.theme = user?.prefs?.theme === "dark" ? "dark" : "light"; }, [user]);
  return <C.Provider value={{ user, loading, setUser, refresh }}>{children}</C.Provider>;
}
