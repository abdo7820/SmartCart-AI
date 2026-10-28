import { when } from "../../api";
import { useGet } from "../../hooks";
import { Status } from "../../components.jsx";

export default function Audit() {
  const r = useGet("/admin/audit", { limit: 100 });
  return (
    <>
      <h1>Audit log</h1>
      <Status loading={r.loading} error={r.error}>
        {r.data && (r.data.length === 0 ? <p className="muted">No audited actions yet.</p> : (
          <table>
            <thead><tr><th>When</th><th>Actor</th><th>Action</th><th>Target</th><th>Details</th></tr></thead>
            <tbody>{r.data.map((e, i) => <tr key={i}><td>{when(e.ts)}</td><td>{e.actor_email || "system"}</td><td>{e.action}</td><td>{e.target || "-"}</td><td className="small">{JSON.stringify(e.details)}</td></tr>)}</tbody>
          </table>
        ))}
      </Status>
    </>
  );
}
