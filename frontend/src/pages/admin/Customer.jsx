import { useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { money, pct } from "../../api";
import { useGet } from "../../hooks";
import { Grid, ProductCard, Status } from "../../components.jsx";

export function ChurnBox({ id }) {
  const c = useGet(`/customers/${id}/churn`);
  return (
    <Status loading={c.loading} error={c.error}>
      {c.data && (c.data.scored ? (
        <div className={`card churn ${c.data.tier.toLowerCase()}`}>
          <div className="row"><span className={`tier ${c.data.tier.toLowerCase()}`}>{c.data.tier} risk</span><span className="big">{pct(c.data.churn_probability)}</span></div>
          <p><strong>Suggested action:</strong> {c.data.action}</p>
          <p className="muted">Main reasons</p>
          <ul>{c.data.reasons.map((r) => <li key={r.feature}>{r.label} = {Number(r.value).toLocaleString(undefined, { maximumFractionDigits: 1 })} ({r.effect})</li>)}</ul>
          <p className="muted small">{c.data.definition}</p>
        </div>
      ) : <p className="card muted">{c.data.reason}</p>)}
    </Status>
  );
}

export default function AdminCustomer() {
  const { id } = useParams();
  const nav = useNavigate();
  const [text, setText] = useState(id || "");
  const cust = useGet(id ? `/customers/${id}` : "/health");
  const [task, setTask] = useState("discovery");
  const recs = useGet(id ? `/customers/${id}/recommendations` : "/health", id ? { k: 12, in_stock_only: "true", task } : {});
  return (
    <>
      <h1>Customer</h1>
      <form className="filters" onSubmit={(e) => { e.preventDefault(); if (text.trim()) nav(`/admin/customer/${text.trim()}`); }}>
        <input value={text} onChange={(e) => setText(e.target.value)} placeholder="Visitor id, for example 109717" aria-label="Visitor id" />
        <button type="submit">Open</button>
      </form>
      {!id ? <p className="muted">Enter a visitor id to see the customer, their recommendations and churn risk.</p> : (
        <Status loading={cust.loading} error={cust.error}>
          {cust.data && cust.data.customer && (
            <>
              <div className="stats">
                <div className="card stat"><b>{cust.data.customer.n_events.toLocaleString()}</b><span>events</span></div>
                <div className="card stat"><b>{cust.data.customer.n_sessions}</b><span>sessions</span></div>
                <div className="card stat"><b>{cust.data.customer.n_orders}</b><span>orders</span></div>
                <div className="card stat"><b>{cust.data.features?.segment_rule || "-"}</b><span>segment</span></div>
              </div>
              <h2>Churn risk</h2>
              <ChurnBox id={id} />
              <h2>Recommended for this customer</h2>
              <div className="filters">
                <select value={task} onChange={(e) => setTask(e.target.value)} aria-label="Recommendation type">
                  <option value="discovery">New items to discover</option>
                  <option value="purchase">Likely next purchase</option>
                  <option value="hybrid">Hybrid (no model)</option>
                </select>
              </div>
              <Status loading={recs.loading} error={recs.error}>
                {recs.data && recs.data.items && (
                  <>
                    <p className="muted">{recs.data.mode === "cold_start" ? "No history, showing popular items." : "Based on this customer's visits and history."} {recs.data.method}</p>
                    <Grid>{recs.data.items.map((p) => <ProductCard key={p.item_id} p={p} note={p.sources.length ? `from: ${p.sources.join(", ")}` : ""} />)}</Grid>
                  </>
                )}
              </Status>
            </>
          )}
        </Status>
      )}
    </>
  );
}
