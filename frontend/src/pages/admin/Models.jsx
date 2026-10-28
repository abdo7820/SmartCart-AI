import { useGet } from "../../hooks";
import { Status } from "../../components.jsx";

function Table({ rows }) {
  if (!rows || rows.length === 0) return <p className="muted">Not available.</p>;
  const cols = Object.keys(rows[0]);
  return (
    <div className="scroll">
      <table>
        <thead><tr>{cols.map((c) => <th key={c}>{c}</th>)}</tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i}>{cols.map((c) => <td key={c}>{r[c] === null ? "-" : String(r[c])}</td>)}</tr>)}</tbody>
      </table>
    </div>
  );
}

export default function Models() {
  const r = useGet("/admin/models");
  return (
    <>
      <h1>Models</h1>
      <Status loading={r.loading} error={r.error}>
        {r.data && (
          <>
            <table><tbody>
              <tr><td>Churn model</td><td>{r.data.serving.churn_model} (High risk from {r.data.serving.churn_threshold})</td></tr>
              <tr><td>Discovery ranking</td><td>{r.data.serving.discovery_final}</td></tr>
              <tr><td>Purchase ranking</td><td>{r.data.serving.purchase_final}</td></tr>
              <tr><td>Rankers loaded</td><td>{r.data.serving.ranker_loaded ? "yes" : "no"}</td></tr>
              <tr><td>Training environment</td><td>{Object.entries(r.data.environment).map(([k, v]) => `${k} ${v}`).join(", ")}</td></tr>
            </tbody></table>
            <h2>Trained models</h2>
            <Table rows={r.data.models} />
            <h2>Recommendation metrics</h2>
            <Table rows={r.data.recommendation_metrics} />
            <h2>Churn test metrics</h2>
            <Table rows={r.data.churn_test_metrics} />
          </>
        )}
      </Status>
    </>
  );
}
