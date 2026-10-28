import { useEffect, useState } from "react";
import { del, get, put } from "../api";
import { useAuth } from "../auth.jsx";
import { Status } from "../components.jsx";
import { useGet } from "../hooks";
import { Icon } from "../ui.jsx";

export default function Profile() {
  const { setUser } = useAuth();
  const me = useGet("/me");
  const activity = useGet("/me/activity", { limit: 1 });
  const [name, setName] = useState("");
  const [country, setCountry] = useState("");
  const [avail, setAvail] = useState([]);
  const [picked, setPicked] = useState([]);
  const [msg, setMsg] = useState("");
  const [error, setError] = useState("");

  useEffect(() => { if (me.data) { setName(me.data.account.full_name); setCountry(me.data.profile.country || ""); } }, [me.data]);
  useEffect(() => { get("/me/preferences").then((result) => { setPicked(result.departments); setAvail(result.available); }).catch((err) => setError(err.message)); }, []);

  const run = async (fn, success) => { setMsg(""); setError(""); try { await fn(); setMsg(success); } catch (err) { setError(err.message); } };
  const saveProfile = (event) => { event.preventDefault(); run(async () => { const result = await put("/me/profile", { full_name: name, country }); setUser(result.account); }, "Profile saved"); };
  const toggle = (department) => setPicked((current) => current.includes(department) ? current.filter((item) => item !== department) : [...current, department]);

  return <div className="profile-wrap account-page"><div className="account-heading"><div><div className="eyebrow">YOUR ACCOUNT</div><h1>Profile &amp; preferences</h1><p className="muted">Keep your details current and tune the signals used for recommendations.</p></div><span className="account-badge"><Icon name="user" />Personal account</span></div><Status loading={me.loading} error={me.error}>{me.data && <p className="account-meta">{me.data.account.email} · {me.data.profile.linked_to_historical_customer ? "Linked to an existing shop history" : "New account"}{activity.data?.length ? " · Activity is available on your dashboard" : ""}</p>}</Status>{msg && <p role="status" className="success-callout"><Icon name="check" />{msg}</p>}{error && <p role="alert" className="error-callout"><Icon name="alert" />{error}</p>}
    <div className="account-grid"><form className="card account-card" onSubmit={saveProfile}><div className="card-kicker">PERSONAL DETAILS</div><h2>Profile details</h2><p className="muted small">This information is used to personalize your experience.</p><label htmlFor="n">Full name</label><input id="n" value={name} onChange={(event) => setName(event.target.value)} autoComplete="name" required /><label htmlFor="c">Country</label><input id="c" value={country} onChange={(event) => setCountry(event.target.value)} autoComplete="country-name" /><button type="submit" disabled={name.trim().length < 2}>Save changes</button></form>
      <section className="card account-card"><div className="card-kicker">RECOMMENDATIONS</div><h2>Your interests</h2><p className="muted small">Choose up to 10 departments to guide recommendations until enough activity is available.</p><div className="chips">{avail.map((department) => <label key={department} className={`chip ${picked.includes(department) ? "on" : ""}`}><input type="checkbox" checked={picked.includes(department)} onChange={() => toggle(department)} />{department}</label>)}</div><button disabled={picked.length > 10} onClick={() => run(() => put("/me/preferences", { departments: picked }), "Interests saved")}>Save interests</button></section>
      <section className="card account-card privacy-card"><div className="card-kicker">PRIVACY</div><h2>Conversation history</h2><p className="muted small">Assistant conversations are stored so you can return to them. You can delete them at any time.</p><button className="danger" onClick={() => { if (confirm("Delete all your assistant conversations?")) run(() => del("/chat/conversations"), "Conversations deleted"); }}><Icon name="trash" />Delete chat history</button></section></div>
  </div>;
}
