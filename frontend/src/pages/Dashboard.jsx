import { Link, useNavigate } from "react-router-dom";
import { useState } from "react";
import { useGet } from "../hooks";
import { Grid, ProductCard, SourceTag, Status } from "../components.jsx";
import { useAuth } from "../auth.jsx";
import { Categories } from "./Home.jsx";
import { imageForDepartment } from "../productImages.js";
import { ActivityIcon, Icon, ago } from "../ui.jsx";

function Assistant() {
  const nav = useNavigate();
  const [query, setQuery] = useState("");
  return <div className="card assist"><div className="head"><span className="bot"><Icon name="bot" /></span><div><h3>AI shopping assistant</h3><p className="muted small" style={{ margin: 0 }}>Ask about products or get recommendations.</p></div></div><form onSubmit={(event) => { event.preventDefault(); nav(query.trim() ? `/chat?q=${encodeURIComponent(query.trim())}` : "/chat"); }}><input value={query} maxLength={500} onChange={(event) => setQuery(event.target.value)} placeholder="Ask for products, gifts, or ideas" aria-label="Ask the assistant" /><button type="submit" aria-label="Send"><Icon name="send" /></button></form></div>;
}

function Activity() {
  const activity = useGet("/me/activity", { limit: 6 });
  return <><div className="section-head"><div><div className="eyebrow">YOUR JOURNEY</div><h2>My activity</h2></div></div><Status loading={activity.loading} error={activity.error}>{activity.data && (activity.data.length === 0 ? <p className="muted">Open a product and it will show up here.</p> : <div className="activity">{activity.data.map((event, index) => <Link key={index} to={`/product/${event.product.item_id}`} className="act"><ActivityIcon eventType={event.event_type} /><div><div className="small muted">{event.event_type === "view" ? "Viewed" : "Added to cart"}</div><div style={{ fontWeight: 600 }}>{event.product.name}</div><div className="small muted">{ago(event.ts)}</div></div></Link>)}</div>)}</Status></>;
}

function RecommendationState({ result, refresh }) {
  if (result.loading && !result.data) return <div className="recommendation-skeleton">{[1, 2, 3, 4].map((item) => <div className="skeleton-card" key={item}><span /><b /><i /></div>)}</div>;
  if (result.error && !result.data) return <div className="error-state" role="alert"><span>{result.error.message}</span><button className="ghost" onClick={() => refresh()}><Icon name="refresh" />Try again</button></div>;
  return result.data?.sections.map((section) => <section key={section.key} className="recommendation-section"><div className="section-head"><div><div className="eyebrow">{section.source === "history_based" ? "PERSONALIZED FOR YOU" : "DISCOVER MORE"}</div><h2>{section.title} <SourceTag source={section.source} /></h2></div><span className="muted small">{section.note}</span></div>{section.items.length === 0 ? <p className="muted">Nothing to show yet.</p> : <Grid>{section.items.map((product, index) => <ProductCard key={product.item_id} p={product} note={product.reason} badge={section.key === "popular" ? `#${index + 1} popular` : section.key === "trending" ? "Trending" : null} tone={section.key === "popular" ? "pop" : "ok"} />)}</Grid>}</section>);
}

export default function Dashboard() {
  const { user } = useAuth();
  const recommendations = useGet("/me/recommendations", { k: 12 });
  const firstName = user?.full_name?.trim()?.split(/\s+/)[0] || "there";
  const heroImage = imageForDepartment(recommendations.data?.sections?.[0]?.items?.[0]?.department || "Electronics");
  return <><section className="hero customer-hero customer-dashboard-hero"><div><div className="eyebrow">YOUR SMARTCART</div><h1>Good to see you, {firstName}.</h1><p>{recommendations.data && !recommendations.data.needs_preferences ? "Here is a fresh selection shaped by your activity and interests." : "Choose a few interests and your recommendations will become more useful over time."}</p><div className="hero-actions"><Link className="btn" to="/products">Explore products</Link>{recommendations.data?.needs_preferences && <Link className="btn ghost" to="/profile">Choose interests</Link>}</div></div><div className="dashboard-hero-image" aria-hidden="true"><img src={heroImage} alt="" /><div><Icon name="spark" /><span>Curated for you</span></div></div></section><Categories /><RecommendationState result={recommendations} refresh={recommendations.refresh} /><Activity /><div style={{ marginTop: 30 }}><Assistant /></div></>;
}
