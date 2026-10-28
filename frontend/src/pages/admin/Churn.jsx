import { Link } from "react-router-dom";
import { pct } from "../../api";
import { useGet } from "../../hooks";
import { Stat, Status } from "../../components.jsx";

export default function Churn() {
  const r = useGet("/admin/churn", { candidates: 2000 });
  return (
    <>
      <h1>Churn</h1>
      <Status loading={r.loading} error={r.error}>
        {r.data && (r.data.scored === 0 ? <p>{r.data.population}</p> : (
          <>
            <p className="muted">Scored {r.data.scored.toLocaleString()} customers: {r.data.population}. {r.data.definition}</p>
            <p className="muted small">These are historical dataset customers. Accounts created in this application have no purchases and are not scored.</p>
            <div className="stats">
              {r.data.tiers.map((t) => <Stat key={t.tier} value={t.customers} label={`${t.tier} risk${t.mean_probability !== null ? `, mean ${pct(t.mean_probability)}` : ""}`} />)}
            </div>
            <h2>Highest risk</h2>
            <table>
              <thead><tr><th>Customer</th><th>Risk</th><th>Tier</th><th>Suggested action</th></tr></thead>
              <tbody>{r.data.top.map((c) => (
                <tr key={c.visitor_id}><td><Link to={`/admin/customer/${c.visitor_id}`}>{c.visitor_id}</Link></td><td>{pct(c.churn_probability)}</td><td><span className={`tier ${c.tier.toLowerCase()}`}>{c.tier}</span></td><td>{c.action}</td></tr>
              ))}</tbody>
            </table>
          </>
        ))}
      </Status>
    </>
  );
}
