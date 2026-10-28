import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { Icon } from "../ui.jsx";

export default function Register() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fields, setFields] = useState({ full_name: "", email: "", password: "", country: "" });
  const [errors, setErrors] = useState({});
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const set = (key) => (event) => setFields((current) => ({ ...current, [key]: event.target.value }));
  const submit = async (event) => { event.preventDefault(); setBusy(true); setErrors({}); setError(""); try { const payload = { full_name: fields.full_name, email: fields.email, password: fields.password }; if (fields.country.trim()) payload.country = fields.country.trim(); const result = await register(payload); navigate(result.redirect, { replace: true }); } catch (err) { setErrors(err.fields || {}); setError(Object.keys(err.fields || {}).length ? "" : err.message); } finally { setBusy(false); } };
  const field = (id, label, props = {}) => <><label htmlFor={id}>{label}</label><input id={id} value={fields[id]} onChange={set(id)} aria-invalid={!!errors[id]} aria-describedby={errors[id] ? `${id}-err` : undefined} {...props} />{errors[id] && <p className="error-callout" id={`${id}-err`} role="alert"><Icon name="alert" />{errors[id]}</p>}</>;
  return <div className="auth-layout"><aside className="auth-visual register-visual"><span className="auth-mark">S</span><div className="eyebrow">MAKE IT YOURS</div><h2>Better picks start with better signals.</h2><p>Choose interests now, then let real activity improve the recommendations you see.</p><div className="auth-points"><span><Icon name="heart" />Save your interests</span><span><Icon name="bot" />Ask the shopping assistant</span></div></aside><form className="card form auth-form" onSubmit={submit} noValidate><div className="card-kicker">SMARTCART AI</div><h1>Create your account</h1><p className="muted small">Free to join. Your activity stays connected to your account.</p>{field("full_name", "Full name", { autoComplete: "name", required: true })}{field("email", "Email", { type: "email", autoComplete: "email", required: true })}{field("password", "Password", { type: "password", autoComplete: "new-password", required: true })}<p className="muted small password-hint">At least 10 characters with letters and digits. It must not contain your name or the first part of your email.</p>{field("country", "Country (optional)", { autoComplete: "country-name" })}{error && <p className="error-callout" role="alert"><Icon name="alert" />{error}</p>}<button type="submit" disabled={busy || !fields.full_name || !fields.email || !fields.password}>{busy ? "Creating..." : "Create account"}</button><p className="muted small auth-switch">Already have an account? <Link to="/login">Log in</Link></p></form></div>;
}
