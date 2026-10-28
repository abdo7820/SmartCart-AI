import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Navigate, useLocation } from "react-router-dom";
import { get, post, setCsrf } from "./api";

const Ctx = createContext(null);
export const useAuth = () => useContext(Ctx);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [expired, setExpired] = useState(false);

  const apply = useCallback((res) => {
    setCsrf(res ? res.csrf_token : null);
    setUser(res ? res.account : null);
  }, []);

  useEffect(() => {
    get("/auth/me").then(apply).catch(() => apply(null)).finally(() => setLoading(false));
  }, [apply]);

  useEffect(() => {
    const onExpired = () => { setCsrf(null); setUser((u) => { if (u) setExpired(true); return null; }); };
    window.addEventListener("auth:expired", onExpired);
    return () => window.removeEventListener("auth:expired", onExpired);
  }, []);

  const login = async (email, password) => {
    const res = await post("/auth/login", { email, password });
    setExpired(false);
    apply(res);
    return res;
  };
  const register = async (payload) => {
    const res = await post("/auth/register", payload);
    setExpired(false);
    apply(res);
    return res;
  };
  const logout = async () => {
    try { await post("/auth/logout"); } catch { /* the session is dropped locally either way */ }
    apply(null);
  };
  return <Ctx.Provider value={{ user, loading, expired, login, register, logout, setUser }}>{children}</Ctx.Provider>;
}

export function RequireAuth({ children, admin = false }) {
  const { user, loading, expired } = useAuth();
  const loc = useLocation();
  if (loading) return <p className="muted">Loading…</p>;
  if (!user) return <Navigate to="/login" state={{ from: loc.pathname, expired }} replace />;
  if (admin && user.role !== "admin") return <Navigate to="/dashboard" replace />;
  if (!admin && user.role === "admin" && loc.pathname.startsWith("/dashboard")) return <Navigate to="/admin" replace />;
  return children;
}
