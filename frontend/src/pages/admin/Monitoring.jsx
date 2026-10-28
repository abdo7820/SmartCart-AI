import { useGet } from "../../hooks";
import { Status } from "../../components.jsx";
import { ADMIN_MONITORING_PATH } from "../../api";

const pct = (value) => value == null ? "Unavailable" : `${Number(value).toFixed(1)}%`;

export default function Monitoring() {
  const result = useGet(ADMIN_MONITORING_PATH);
  return <>
    <div className="admin-heading"><div><h1>Monitoring</h1><p className="muted">Local system, model inference, and data-quality signals.</p></div><button className="btn ghost" onClick={result.refresh}>Refresh</button></div>
    <Status loading={result.loading} error={result.error}>
      {result.data && <>
        <div className="monitoring-grid">
          <Metric label="CPU" value={pct(result.data.system?.cpu_percent)} />
          <Metric label="Memory" value={pct(result.data.system?.memory_percent)} />
          <Metric label="Disk" value={pct(result.data.system?.disk_percent)} />
          <Metric label="Models observed" value={result.data.models?.length || 0} />
        </div>
        <section className="monitoring-panel"><h2>Alerts</h2>{result.data.alerts?.length ? <div className="monitoring-alerts">{result.data.alerts.map((alert, i) => <div className={`monitoring-alert ${alert.severity}`} key={i}><strong>{alert.title}</strong><span>{alert.detail}</span></div>)}</div> : <p className="ok">No configured monitoring alerts.</p>}</section>
        <section className="monitoring-panel"><h2>Model inference</h2>{result.data.models?.length ? <div className="scroll"><table><thead><tr><th>Model</th><th>Version</th><th>Predictions</th><th>Failures</th><th>Avg duration</th></tr></thead><tbody>{result.data.models.map((model) => <tr key={`${model.model_name}-${model.model_version}`}><td>{model.model_name}</td><td>{model.model_version}</td><td>{model.predictions}</td><td>{model.failures}</td><td>{model.avg_duration_ms} ms</td></tr>)}</tbody></table></div> : <p className="muted">No inference observations in the configured window.</p>}</section>
        <section className="monitoring-panel"><h2>Latest data-quality report</h2>{result.data.latest_drift ? <p><strong>{result.data.latest_drift.status}</strong> · {result.data.latest_drift.dataset_name || "dataset"} · drifted columns: {(result.data.latest_drift.drifted_columns || []).join(", ") || "none"}</p> : <p className="muted">No reference/current comparison has been recorded yet.</p>}</section>
        <p className="small muted">Window: {result.data.window_hours} hours. This page intentionally does not collect HTTP request counts, latency, or HTTP error rates.</p>
      </>}
    </Status>
  </>;
}

function Metric({ label, value }) { return <div className="monitoring-metric"><span className="small muted">{label}</span><strong>{value}</strong></div>; }
