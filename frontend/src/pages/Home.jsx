import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../auth.jsx";
import { useGet } from "../hooks";
import { Grid, ProductCard, Status } from "../components.jsx";
import { Icon } from "../ui.jsx";
import { imageForDepartment } from "../productImages.js";

export function Categories() {
  const categories = useGet("/categories");
  if (!categories.data) return null;
  return <div className="cats" aria-label="Shop by category">{categories.data.slice(0, 8).map((category) => <Link key={category.department} to={`/products?department=${encodeURIComponent(category.department)}`} className="cat"><span className="cat-image"><img src={imageForDepartment(category.department)} alt="" loading="lazy" /></span><strong>{category.department}</strong><small>{category.products.toLocaleString()} products</small></Link>)}</div>;
}

const HERO_DEPARTMENTS = ["Electronics", "Fashion", "Home & Kitchen", "Sports & Outdoors"];

export default function Home() {
  const { user } = useAuth();
  const popular = useGet("/products", { sort: "popular", limit: 8, in_stock: "true" });
  if (user) return <Navigate to={user.role === "admin" ? "/admin" : "/dashboard"} replace />;
  return <>
    <section className="hero customer-hero"><div><div className="eyebrow">SMARTER SHOPPING, LESS SEARCHING</div><h1>Find products that fit your life.</h1><p>Explore a curated catalog, discover useful recommendations, and ask the SmartCart AI assistant when you need a better starting point.</p><div className="hero-actions"><Link className="btn" to="/register">Create an account</Link><Link className="btn ghost" to="/products"><Icon name="search" />Browse products</Link></div></div><div className="hero-art image-art" aria-hidden="true">{HERO_DEPARTMENTS.map((department) => <span key={department}><img src={imageForDepartment(department)} alt="" /></span>)}</div></section>
    <div className="section-head"><div><div className="eyebrow">EXPLORE THE CATALOG</div><h2>Shop by category</h2></div><Link to="/products">View all products <Icon name="arrow" /></Link></div>
    <Categories />
    <div className="section-head"><div><div className="eyebrow">POPULAR RIGHT NOW</div><h2>Popular products</h2></div><Link to="/products?sort=popular">See all <Icon name="arrow" /></Link></div>
    <Status loading={popular.loading} error={popular.error}>{popular.data && <Grid>{popular.data.items.map((product, index) => <ProductCard key={product.item_id} p={product} badge={`#${index + 1} popular`} tone="pop" />)}</Grid>}</Status>
  </>;
}
