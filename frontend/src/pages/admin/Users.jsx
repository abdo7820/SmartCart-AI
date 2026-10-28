import { useState } from "react";
import { post, when } from "../../api";
import { useGet } from "../../hooks";
import { Status } from "../../components.jsx";
import { useAuth } from "../../auth.jsx";

const PAGE = 25;

export default function Users() {
  const { user } = useAuth();
  const [q, setQ] = useState("");
  const [term, setTerm] = useState("");
  const [page, setPage] = useState(0);
  const [tick, setTick] = useState(0);
  const [error, setError] = useState("");
  const [link, setLink] = useState({});
  const r = useGet("/admin/users", { q: term, limit: PAGE, offset: page * PAGE, t: tick });

  const act = async (fn) => {
    setError("");
    try { await fn(); setTick((t) => t + 1); } catch (e) { setError(e.message); }
  };
  const pages = r.data ? Math.max(1, Math.ceil(r.data.total / PAGE)) : 1;

  return (
    <>
      <h1>Users</h1>
      <form className="filters" onSubmit={(e) => { e.preventDefault(); setPage(0); setTerm(q); }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search name or email" aria-label="Search users" />
        <button type="submit">Search</button>
      </form>
      <p className="muted small">Linking connects an account to an existing historical customer id from the dataset. Do this only when you have verified that the person owns that history.</p>
      {error && <p role="alert" className="error">{error}</p>}
      <Status loading={r.loading} error={r.error}>
        {r.data && (
          <>
            <table>
              <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Last login</th><th>History</th><th>Actions</th></tr></thead>
              <tbody>
                {r.data.items.map((u) => (
                  <tr key={u.id}>
                    <td>{u.full_name}<br /><span className="muted small">{u.email}</span></td>
                    <td>{u.role}</td>
                    <td>{u.is_active ? "Active" : "Disabled"}</td>
                    <td>{when(u.last_login_at)}</td>
                    <td>
                      {u.historical_visitor_id ? <>customer {u.historical_visitor_id} <button className="ghost" onClick={() => act(() => post(`/admin/users/${u.id}/unlink-visitor`))}>Unlink</button></> : (
                        <form className="inline" onSubmit={(e) => { e.preventDefault(); act(() => post(`/admin/users/${u.id}/link-visitor`, { visitor_id: Number(link[u.id]) })); }}>
                          <input className="narrow" inputMode="numeric" placeholder="customer id" aria-label={`Customer id for ${u.email}`} value={link[u.id] || ""} onChange={(e) => setLink({ ...link, [u.id]: e.target.value })} />
                          <button className="ghost" type="submit" disabled={!/^\d+$/.test(link[u.id] || "")}>Link</button>
                        </form>
                      )}
                    </td>
                    <td>
                      {u.id === user.id ? <span className="muted small">you</span> : u.is_active
                        ? <button className="danger" onClick={() => { if (confirm(`Disable ${u.email}?`)) act(() => post(`/admin/users/${u.id}/disable`)); }}>Disable</button>
                        : <button onClick={() => act(() => post(`/admin/users/${u.id}/enable`))}>Enable</button>}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="pager">
              <button disabled={page === 0} onClick={() => setPage(page - 1)}>Previous</button>
              <span>Page {page + 1} of {pages}</span>
              <button disabled={page + 1 >= pages} onClick={() => setPage(page + 1)}>Next</button>
            </div>
          </>
        )}
      </Status>
    </>
  );
}
