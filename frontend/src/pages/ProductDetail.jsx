import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { money, pct, post } from "../api";
import { useAuth } from "../auth.jsx";
import { useGet } from "../hooks";
import { Grid, ProductCard, ProductVisual, Status, Stock } from "../components.jsx";
import { Icon } from "../ui.jsx";

export default function ProductDetail() {
  const { id } = useParams();
  const product = useGet(`/products/${id}`);
  const similar = useGet(`/products/${id}/similar`, { k: 8 });
  const { user } = useAuth();
  const isUser = user?.role === "user";
  const [notice, setNotice] = useState("");
  useEffect(() => { setNotice(""); if (isUser) post("/me/events", { event_type: "view", item_id: Number(id) }).catch(() => {}); }, [id, isUser]);
  const recordInterest = async () => { try { await post("/me/events", { event_type: "addtocart", item_id: Number(id) }); setNotice("Interest recorded. This helps improve your recommendations; a shopping cart and checkout are not implemented yet."); } catch (error) { setNotice(error.message); } };

  return <Status loading={product.loading} error={product.error}>{product.data && <><nav className="breadcrumbs" aria-label="Breadcrumb"><Link to="/">Home</Link><Icon name="arrow" /><Link to={`/products?department=${encodeURIComponent(product.data.department)}`}>{product.data.department}</Link><Icon name="arrow" /><span>{product.data.name}</span></nav><div className="detail product-detail-card"><ProductVisual p={product.data} big /><div className="detail-copy"><span className="detail-kicker">{product.data.department} · {product.data.product_type}</span><h1>{product.data.name}</h1><p className="detail-brand">{product.data.brand}</p><div className="detail-price-row"><span className="price detail-price">{money(product.data.price, product.data.currency)}</span>{product.data.is_deal ? <span className="tag deal">Deal</span> : null}<Stock value={product.data.in_stock} /></div><p className="detail-note">A representative product image is shown when the catalog does not provide a product-specific asset.</p><dl className="detail-stats"><div><dt>Price tier</dt><dd>{product.data.price_tier}</dd></div><div><dt>Views</dt><dd>{product.data.n_views.toLocaleString()}</dd></div><div><dt>Added to cart</dt><dd>{product.data.n_carts.toLocaleString()}</dd></div><div><dt>Purchases</dt><dd>{product.data.n_purchases.toLocaleString()}</dd></div><div><dt>View to cart</dt><dd>{pct(product.data.view_to_cart || 0)}</dd></div></dl>{isUser && <div className="detail-actions"><button onClick={recordInterest}><Icon name="heart" />Save interest</button><Link className="btn ghost" to={`/chat?item=${id}`}><Icon name="bot" />Ask the assistant</Link></div>}{!user && <p className="muted small detail-login"><Link to="/login">Log in</Link> to save interest and ask the assistant about this product.</p>}{notice && <p role="status" className="success-callout"><Icon name="check" />{notice}</p>}{product.data.price_is_synthetic && <p className="muted small">Name, brand, and price are generated catalog fields.</p>}</div></div><section className="related-section"><div className="section-head"><div><div className="eyebrow">KEEP EXPLORING</div><h2>Customers also looked at</h2></div><Link to={`/products?department=${encodeURIComponent(product.data.department)}`}>More in {product.data.department} <Icon name="arrow" /></Link></div><Status loading={similar.loading} error={similar.error}>{similar.data && (similar.data.items.length === 0 ? <p className="muted">No similar products are available for this item yet.</p> : <Grid>{similar.data.items.map((item) => <ProductCard key={item.item_id} p={item} />)}</Grid>)}</Status></section></>}</Status>;
}
