import { useState } from "react";
import { Link } from "react-router-dom";
import { money } from "./api";
import { deptLook, tint, Icon, productIconName } from "./ui.jsx";
import { resolveProductImageCandidates } from "./productImages.js";

export function Status({ loading, error, children }) {
  if (loading) return <p className="muted">Loading…</p>;
  if (error) return <p className="error" role="alert">{error.message}</p>;
  return children;
}

export function Stock({ value }) {
  if (value === 1) return <span className="tag ok">In stock</span>;
  if (value === 0) return <span className="tag off">Out of stock</span>;
  return <span className="tag plain">Stock unknown</span>;
}

export function Thumb({ dept, badge, tone = "ok", big }) {
  const { hue } = deptLook(dept);
  return (
    <div className="thumb" style={{ background: `linear-gradient(135deg, ${tint(hue, 95)}, ${tint(hue, 86)})`, fontSize: big ? 96 : undefined }} aria-hidden="true">
      <Icon name={productIconName(dept)} label={`${dept || "Product"} category`} />
      {badge ? <span className={`badge ${tone}`}>{badge}</span> : null}
    </div>
  );
}

export function ProductVisual({ p, badge, tone, big }) {
  const [failedIndex, setFailedIndex] = useState(0);
  const candidates = resolveProductImageCandidates(p);
  const image = candidates[Math.min(failedIndex, candidates.length - 1)];
  if (!image.src) return <div className={`thumb image-placeholder ${big ? "photo-big" : ""}`} aria-label={`Representative ${p.product_type || p.department || "product"} icon`}><Icon name={productIconName(p)} label={`Representative ${p.product_type || p.department || "product"} icon`} /><span>Representative icon</span><small>{p.product_type || p.department || "Product"}</small>{badge ? <span className={`badge ${tone || "ok"}`}>{badge}</span> : null}</div>;
  return (
    <div className={`thumb photo ${big ? "photo-big" : ""}`}>
      <img src={image.src} alt={`${image.source === "product" ? "Product" : "Representative"} ${p.product_type || p.department} image for ${p.name}`} loading="lazy" decoding="async" onError={() => setFailedIndex((index) => Math.min(index + 1, candidates.length - 1))} />
      {badge ? <span className={`badge ${tone || "ok"}`}>{badge}</span> : null}
    </div>
  );
}

export function ProductCard({ p, note, badge, tone }) {
  const label = badge || (p.is_deal ? "Deal" : null);
  return (
    <Link to={`/product/${p.item_id}`} className="pcard">
      <ProductVisual p={p} badge={label} tone={badge ? tone : "deal"} />
      <div className="pbody">
        <div className="dept">{p.department}</div>
        <div className="pname">{p.name}</div>
        <div className="prow">
          <span className="price">{money(p.price, p.currency || "USD")}</span>
          <Stock value={p.in_stock} />
        </div>
        {note ? <div className="note">{note}</div> : null}
      </div>
    </Link>
  );
}

export function Grid({ children }) {
  return <div className="grid">{children}</div>;
}

export function SourceTag({ source }) {
  const map = {
    history_based: ["Based on your activity", "ok"],
    preference_based: ["Based on your interests", "ok"],
    popularity_based: ["Popular, not personalized", "plain"],
    popularity: ["Popular, not personalized", "plain"],
    trend: ["Trending, not personalized", "plain"],
    activity: ["Your activity", "ok"],
    item_similarity: ["Similar products", "ok"],
  };
  const [text, cls] = map[source] || [source, "plain"];
  return <span className={`tag ${cls}`}>{text}</span>;
}

export function Stat({ value, label }) {
  return <div className="card stat"><b>{typeof value === "number" ? value.toLocaleString() : value}</b><span>{label}</span></div>;
}

export function Kpi({ icon, value, label, sub }) {
  return (
    <div className="card kpi">
      <div><small>{label}</small><b>{typeof value === "number" ? value.toLocaleString() : value}</b>{sub ? <div className="sub">{sub}</div> : null}</div>
      <span className="ic">{icon}</span>
    </div>
  );
}
