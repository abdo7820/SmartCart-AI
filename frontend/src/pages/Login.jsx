import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Icon } from "../ui.jsx";

export default function Login() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [showExpiredNotice, setShowExpiredNotice] = useState(Boolean(location.state?.expired));
  const submit = async (event) => { event.preventDefault(); setBusy(true); setError(""); setShowExpiredNotice(false); try { const result = await login(email, password); const from = location.state?.from; navigate(result.account.role === "admin" ? result.redirect : from && !from.startsWith("/admin") ? from : result.redirect, { replace: true }); } catch (err) { setError(err.message); } finally { setBusy(false); } };
  return <div className="auth-layout"><aside className="auth-visual"><span className="auth-mark">S</span><div className="eyebrow">WELCOME BACK</div><h2>Your smarter way to shop.</h2><p>Pick up where you left off with recommendations shaped by your interests and activity.</p><div className="auth-points"><span><Icon name="shield" />Secure account sessions</span><span><Icon name="spark" />Catalog-aware recommendations</span></div></aside><form className="card form auth-form" onSubmit={submit} noValidate><div className="card-kicker">SMARTCART AI</div><h1>Welcome back</h1><p className="muted small">Log in to continue exploring products and recommendations.</p>{showExpiredNotice && <p className="error-callout" role="alert"><Icon name="clock" />Your session expired. Please log in again.</p>}<label htmlFor="email">Email</label><input id="email" type="email" autoComplete="email" value={email} onChange={(event) => { setEmail(event.target.value); setShowExpiredNotice(false); }} required /><label htmlFor="password">Password</label><input id="password" type="password" autoComplete="current-password" value={password} onChange={(event) => { setPassword(event.target.value); setShowExpiredNotice(false); }} required />{error && <p className="error-callout" role="alert"><Icon name="alert" />{error}</p>}<button type="submit" disabled={busy || !email || !password}>{busy ? "Logging in..." : "Log in"}</button><p className="muted small auth-switch">New here? <Link to="/register">Create an account</Link></p></form></div>;
}
