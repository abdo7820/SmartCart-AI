const ICONS = {
  home: "M3 11l9-8 9 8M5 10v10h14V10",
  box: "M21 8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v8",
  users: "M16 20v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2M9 10a4 4 0 100-8 4 4 0 000 8zM22 20v-2a4 4 0 00-3-3.9M16 2.1a4 4 0 010 7.8",
  churn: "M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6z",
  chart: "M3 3v18h18M7 15l4-4 3 3 5-6",
  list: "M8 6h13M8 12h13M8 18h13M3 6h.01M3 12h.01M3 18h.01",
  search: "M21 21l-4.3-4.3M11 18a7 7 0 100-14 7 7 0 000 14z",
  bot: "M12 8V4M8 4h8M5 8h14a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2v-8a2 2 0 012-2zM9 14h.01M15 14h.01",
  send: "M22 2L11 13M22 2l-7 20-4-9-9-4z",
  logout: "M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4M16 17l5-5-5-5M21 12H9",
  user: "M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2M12 11a4 4 0 100-8 4 4 0 000 8z",
  cart: "M6 6h15l-1.5 9h-12zM6 6L5 3H2M9 20h.01M18 20h.01",
  eye: "M1 12s4-8 11-8 11 8 11 8-4 8-11 8S1 12 1 12zM12 15a3 3 0 100-6 3 3 0 000 6z",
  cpu: "M9 3v2M15 3v2M9 19v2M15 19v2M3 9h2M3 15h2M19 9h2M19 15h2M7 5h10a2 2 0 012 2v10a2 2 0 01-2 2H7a2 2 0 01-2-2V7a2 2 0 012-2zM9 9h6v6H9z",
  lookup: "M16 11a5 5 0 11-10 0 5 5 0 0110 0zM21 21l-4-4",
  database: "M4 6c0-2 4-3 8-3s8 1 8 3-4 3-8 3-8-1-8-3zm0 0v6c0 2 4 3 8 3s8-1 8-3V6m-16 6v6c0 2 4 3 8 3s8-1 8-3v-6",
  activity: "M3 12h4l2-7 4 14 2-7h6",
  alert: "M10.3 4.3L2.6 17.2A2 2 0 004.3 20h15.4a2 2 0 001.7-2.8L13.7 4.3a2 2 0 00-3.4 0zM12 9v4m0 3h.01",
  check: "M20 6L9 17l-5-5",
  info: "M12 16v-4m0-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  arrow: "M5 12h14m-6-6 6 6-6 6",
  "arrow-left": "M19 12H5m6 6-6-6 6-6",
  refresh: "M20 11a8 8 0 00-14.9-3.9L3 10m0 0V5m0 5h5M4 13a8 8 0 0014.9 3.9L21 14m0 0v5m0-5h-5",
  clock: "M12 6v6l4 2m5-2a9 9 0 11-18 0 9 9 0 0118 0z",
  shield: "M12 2l8 4v6c0 5-3.5 8.5-8 10-4.5-1.5-8-5-8-10V6zM9 12l2 2 4-4",
  menu: "M4 6h16M4 12h16M4 18h16",
  close: "M6 6l12 12M18 6L6 18",
  spark: "M12 3l1.8 5.2L19 10l-5.2 1.8L12 17l-1.8-5.2L5 10l5.2-1.8L12 3zM19 16l.8 2.2L22 19l-2.2.8L19 22l-.8-2.2L16 19l2.2-.8L19 16z",
  trash: "M4 7h16M10 11v6M14 11v6M6 7l1 14h10l1-14M9 7V4h6v3",
  heart: "M20.8 8.6c0 5.5-8.8 10.4-8.8 10.4S3.2 14.1 3.2 8.6A4.6 4.6 0 0112 6.1a4.6 4.6 0 018.8 2.5z",
  "cart-plus": "M6 6h15l-1.5 9h-12zM6 6L5 3H2M9 20h.01M18 20h.01M16 10v4M14 12h4",
  message: "M21 11.5a8.4 8.4 0 01-9 8.5 9.3 9.3 0 01-4-.9L3 21l1.9-4.1A8.2 8.2 0 013 11.5 8.5 8.5 0 0112 3a8.5 8.5 0 019 8.5z",
  "user-check": "M16 21v-2a4 4 0 00-4-4H6a4 4 0 00-4 4v2M9 11a4 4 0 100-8 4 4 0 000 8zM16 11l2 2 4-4",
  "circle-help": "M9.1 9a3 3 0 115.7 1.3c-.8 1-2.8 1.3-2.8 3.2M12 17h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
  headphones: "M3 14v-2a9 9 0 0118 0v2M3 14a2 2 0 002 2h1v-6H5a2 2 0 00-2 2zm18 0a2 2 0 01-2 2h-1v-6h1a2 2 0 012 2zM17 19h-2",
  monitor: "M4 4h16v11H4zM8 20h8M12 15v5",
  blender: "M8 4h8l-1 5H9L8 4zM9 9h6v8a3 3 0 01-6 0V9zM11 20h2",
  "cooking-pot": "M4 10h16v7a3 3 0 01-3 3H7a3 3 0 01-3-3v-7zM2 10h20M8 6a4 4 0 018 0v4M12 3v3",
  shirt: "M9 3l3 2 3-2 5 3-2 5-3-1v10H9V10l-3 1-2-5z",
  footprint: "M8 5.5a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zM19 10.5a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zM6 10c-2 1-3 3-2 5s3 1 4 0 2-3 1-4M15 15c-1 1-1 3 1 4s4 0 4-2-1-3-3-3",
  paw: "M8 10a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zm13 0a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zM12 8a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zm5 0a2.5 2.5 0 11-5 0 2.5 2.5 0 015 0zm-2 11c-1 2-4 2-5 0-1-2-3-2-3-4 0-2 2-3 4-3s4 1 4 3c0 2-2 2-3 4z",
  house: "M3 11l9-8 9 8M5 10v10h14V10M9 20v-6h6v6",
  "book-open": "M3 5a3 3 0 013-2h5v17H6a3 3 0 01-3-3V5zm18 0a3 3 0 00-3-2h-5v17h5a3 3 0 003-3V5z",
  gamepad: "M6 9h12a4 4 0 013.8 5l-1 4a2 2 0 01-3.5.8L15 16H9l-2.3 2.8a2 2 0 01-3.5-.8l-1-4A4 4 0 016 9zM7 12v4M5 14h4M17 13h.01M19 15h.01",
  package: "M21 8l-9-5-9 5v8l9 5 9-5zM3 8l9 5 9-5M12 13v8",
};
export const Icon = ({ name, label }) => (
  <svg className="ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" role={label ? "img" : undefined} aria-label={label} aria-hidden={label ? undefined : "true"}><path d={ICONS[name] || ICONS.package} /></svg>
);

const DEPT = [
  [/^electronics$/i, "headphones", 245],
  [/^fashion$/i, "shirt", 350],
  [/^home & kitchen$/i, "house", 30],
  [/^beauty & health$/i, "spark", 300],
  [/^sports & outdoors$/i, "activity", 150],
  [/^toys & games$/i, "gamepad", 45],
  [/^books & media$/i, "book-open", 200],
  [/^pet supplies$/i, "paw", 100],
  [/^automotive$/i, "package", 210],
  [/^garden & tools$/i, "package", 120],
];
export function deptLook(name) {
  const hit = DEPT.find(([re]) => re.test(name || ""));
  if (hit) return { icon: hit[1], hue: hit[2] };
  let h = 0;
  for (const c of name || "x") h = (h * 31 + c.charCodeAt(0)) % 360;
  return { icon: "package", hue: h };
}
export const tint = (hue, l = 94) => `hsl(${hue} 80% ${l}%)`;

const ACTIVITY_ICONS = {
  view: "eye", viewed: "eye", addtocart: "cart-plus", search: "search", recommendation: "spark", recommend: "spark", chat: "message", login: "user-check",
};

export function activityIconName(eventType) {
  return ACTIVITY_ICONS[String(eventType || "").toLowerCase()] || "circle-help";
}

export function ActivityIcon({ eventType, size = 46 }) {
  const icon = activityIconName(eventType);
  return <span className="activity-icon" style={{ width: size, height: size }}><Icon name={icon} label={`${eventType || "Unknown"} activity`} /></span>;
}

const PRODUCT_TYPE_ICONS = {
  speaker: "headphones", headphones: "headphones", monitor: "monitor", "computer monitor": "monitor", blender: "blender", kettle: "cooking-pot", toaster: "cooking-pot",
  jacket: "shirt", dress: "shirt", jeans: "shirt", sneakers: "footprint", "running shoes": "footprint", "dog leash": "paw", "pet bowl": "paw", "pet bed": "paw",
  "cat toy": "paw", "bird feeder": "paw", "comic book": "book-open", cookbook: "book-open", dictionary: "book-open", novel: "book-open", "board game": "gamepad", "card game": "gamepad",
  "building blocks": "gamepad", puzzle: "gamepad", "remote car": "gamepad", watch: "package", camera: "package", lamp: "house", curtains: "house", pillow: "house", toolbox: "package", drill: "package",
};

const DEPARTMENT_ICONS = {
  electronics: "headphones", fashion: "shirt", "home & kitchen": "house", "beauty & health": "spark", "sports & outdoors": "activity", "toys & games": "gamepad",
  "pet supplies": "paw", "books & media": "book-open", automotive: "package", "garden & tools": "package",
};

export function productIconName(product) {
  const type = typeof product === "string" ? "" : String(product?.product_type || "").trim().toLowerCase();
  const department = String(typeof product === "string" ? product : product?.department || "").trim().toLowerCase();
  return PRODUCT_TYPE_ICONS[type] || DEPARTMENT_ICONS[department] || "package";
}

export function Donut({ parts, center, size = 150 }) {
  const total = parts.reduce((a, p) => a + p.value, 0);
  const r = 54, c = 2 * Math.PI * r;
  let off = 0;
  return (
    <svg viewBox="0 0 140 140" width={size} height={size} role="img" aria-label={parts.map((p) => `${p.label} ${p.value}`).join(", ")}>
      <circle cx="70" cy="70" r={r} fill="none" stroke="var(--bg)" strokeWidth="18" />
      {total > 0 && parts.map((p) => {
        const len = (p.value / total) * c;
        const el = <circle key={p.label} cx="70" cy="70" r={r} fill="none" stroke={p.color} strokeWidth="18" strokeDasharray={`${len} ${c - len}`} strokeDashoffset={-off} transform="rotate(-90 70 70)" />;
        off += len;
        return el;
      })}
      {center && <><text x="70" y="68" textAnchor="middle" fontSize="19" fontWeight="700" fill="var(--ink)">{center.value}</text><text x="70" y="84" textAnchor="middle" fontSize="9" fill="var(--muted)">{center.label}</text></>}
    </svg>
  );
}

export function AreaChart({ points, labels, color = "var(--brand)", height = 200 }) {
  const W = 640, H = height, L = 44, B = 24, T = 10;
  const max = Math.max(1, ...points);
  const x = (i) => L + (i / Math.max(1, points.length - 1)) * (W - L - 8);
  const y = (v) => T + (1 - v / max) * (H - T - B);
  const line = points.map((v, i) => `${i ? "L" : "M"}${x(i).toFixed(1)} ${y(v).toFixed(1)}`).join(" ");
  const area = `${line} L${x(points.length - 1)} ${H - B} L${x(0)} ${H - B} Z`;
  const ticks = [0, 0.5, 1].map((t) => Math.round(max * t));
  const shown = labels.map((l, i) => [l, i]).filter(([, i]) => i % Math.ceil(labels.length / 6) === 0);
  return (
    <svg className="chart" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Daily activity chart">
      <defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stopColor={color} stopOpacity=".28" /><stop offset="1" stopColor={color} stopOpacity="0" /></linearGradient></defs>
      {ticks.map((t) => <g key={t}><line x1={L} x2={W - 8} y1={y(t)} y2={y(t)} stroke="var(--line)" /><text x={L - 6} y={y(t) + 4} textAnchor="end">{t.toLocaleString()}</text></g>)}
      <path d={area} fill="url(#ag)" />
      <path d={line} fill="none" stroke={color} strokeWidth="2.2" strokeLinejoin="round" />
      {points.map((v, i) => <circle key={i} cx={x(i)} cy={y(v)} r="3" fill={color}><title>{`${labels[i]}: ${v.toLocaleString()}`}</title></circle>)}
      {shown.map(([l, i]) => <text key={i} x={x(i)} y={H - 6} textAnchor="middle">{l}</text>)}
    </svg>
  );
}

export function Bars({ rows, format = (v) => v.toLocaleString() }) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  return (
    <div className="bars">
      {rows.map((r) => (
        <div className="row2" key={r.label}>
          <span title={r.label}>{r.label}</span>
          <div className="track"><div className="fill" style={{ width: `${(r.value / max) * 100}%` }} /></div>
          <b>{format(r.value)}</b>
        </div>
      ))}
    </div>
  );
}

export const ago = (ms) => {
  const s = Math.max(1, Math.round((Date.now() - ms) / 1000));
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.floor(s / 60)} min ago`;
  if (s < 86400) return `${Math.floor(s / 3600)} h ago`;
  return `${Math.floor(s / 86400)} d ago`;
};
