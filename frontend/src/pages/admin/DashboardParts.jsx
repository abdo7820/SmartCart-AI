import { Link } from "react-router-dom";
import { Kpi } from "../../components.jsx";
import { Icon } from "../../ui.jsx";

export function MetricCard({ icon, value, label, sub, to, tone = "brand" }) {
  const card = <Kpi icon={<span className={`kpi-icon ${tone}`}>{icon}</span>} value={value} label={label} sub={sub} />;
  return to ? <Link className="kpi-link" to={to}>{card}</Link> : card;
}

export function PanelHeader({ eyebrow, title, description, action }) {
  return <div className="panel-head"><div>{eyebrow && <div className="eyebrow">{eyebrow}</div>}<h2>{title}</h2>{description && <p className="sub">{description}</p>}</div>{action}</div>;
}

export function StatusPill({ ok, label, tone }) {
  const kind = tone || (ok ? "success" : "danger");
  return <span className={`status-pill ${kind}`}><span className="status-dot" />{label}</span>;
}

export function AlertCard({ alert }) {
  const icons = { critical: "alert", warning: "alert", info: "info", ok: "check" };
  return <div className={`ops-alert ${alert.severity}`}><span className="alert-icon"><Icon name={icons[alert.severity] || "info"} /></span><div className="alert-copy"><div className="alert-title">{alert.title}</div><p>{alert.detail}</p>{alert.href && <Link to={alert.href}>Review details <Icon name="arrow" /></Link>}</div></div>;
}

export function EmptyState({ icon = "activity", title, children }) {
  return <div className="empty-state"><span className="empty-icon"><Icon name={icon} /></span><div><strong>{title}</strong>{children && <p>{children}</p>}</div></div>;
}

export function Definition({ children }) {
  return <span className="definition" title={children} aria-label={children}>i</span>;
}
