import { useState } from "react";
import { Link, NavLink, Navigate, Route, Routes, useLocation, useNavigate } from "react-router-dom";
import { AuthProvider, RequireAuth, useAuth } from "./auth.jsx";
import { useGet } from "./hooks";
import { Icon } from "./ui.jsx";
import Home from "./pages/Home.jsx";
import Products from "./pages/Products.jsx";
import ProductDetail from "./pages/ProductDetail.jsx";
import Login from "./pages/Login.jsx";
import Register from "./pages/Register.jsx";
import Dashboard from "./pages/Dashboard.jsx";
import Chat from "./pages/Chat.jsx";
import Profile from "./pages/Profile.jsx";
import AdminOverview from "./pages/admin/Overview.jsx";
import AdminUsers from "./pages/admin/Users.jsx";
import AdminChurn from "./pages/admin/Churn.jsx";
import AdminModels from "./pages/admin/Models.jsx";
import AdminCustomer from "./pages/admin/Customer.jsx";
import AdminAudit from "./pages/admin/Audit.jsx";
import AdminMonitoring from "./pages/admin/Monitoring.jsx";

const Logo = ({ sub }) => <span className="logo"><i>S</i><span>SmartCart AI<small>{sub}</small></span></span>;

function Banner() {
  const { data, error } = useGet("/health");
  if (error) return <div className="banner bad">The API is not reachable. Start it on port 8000.</div>;
  return null;
}

function ShopTop() {
  const { user, logout } = useAuth();
  const nav = useNavigate();
  const [q, setQ] = useState("");
  const [menuOpen, setMenuOpen] = useState(false);
  const initials = user ? user.full_name.split(" ").map((w) => w[0]).slice(0, 2).join("").toUpperCase() : "";
  const closeMenu = () => setMenuOpen(false);
  return (
    <header className="shop-top">
      <div className="in">
        <NavLink to={user ? "/dashboard" : "/"}><Logo sub="Smart shopping" /></NavLink>
        <button className="mobile-menu" onClick={() => setMenuOpen((open) => !open)} aria-expanded={menuOpen} aria-controls="customer-nav" aria-label={menuOpen ? "Close navigation" : "Open navigation"}><Icon name={menuOpen ? "close" : "menu"} /></button>
        <nav id="customer-nav" className={menuOpen ? "open" : ""} aria-label="Main">
          <NavLink onClick={closeMenu} to={user ? "/dashboard" : "/"} end>Home</NavLink>
          <NavLink onClick={closeMenu} to="/products">Products</NavLink>
          {user && user.role === "user" && <NavLink onClick={closeMenu} to="/chat">AI Assistant</NavLink>}
          {user && user.role === "user" && <NavLink onClick={closeMenu} to="/profile">Profile</NavLink>}
          {user && user.role === "admin" && <NavLink onClick={closeMenu} to="/admin">Admin</NavLink>}
        </nav>
        <form className="shop-search" role="search" onSubmit={(e) => { e.preventDefault(); nav(`/products?q=${encodeURIComponent(q)}`); }}>
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search products" aria-label="Search products" />
          <button type="submit" aria-label="Search"><Icon name="search" /></button>
        </form>
        {user ? (
          <div className="userbox">
            <span className="avatar" aria-hidden="true">{initials}</span>
            <span className="small">{user.full_name.split(" ")[0]}</span>
            <button className="ghost logout-button" onClick={logout}><Icon name="logout" />Log out</button>
          </div>
        ) : (
          <div className="userbox">
            <NavLink to="/login">Log in</NavLink>
            <NavLink to="/register" className="btn">Sign up</NavLink>
          </div>
        )}
      </div>
    </header>
  );
}

const ADMIN_NAV = [
  ["/admin", "Dashboard", "chart", true],
  ["/admin/users", "Users", "users"],
  ["/admin/churn", "Churn", "churn"],
  ["/admin/models", "Models", "cpu"],
  ["/admin/customer", "Customer lookup", "lookup"],
  ["/admin/audit", "Audit log", "list"],
  ["/admin/monitoring", "Monitoring", "activity"],
  ["/products", "View shop", "box"],
];

function AdminShell({ children }) {
  const { user, logout } = useAuth();
  return (
    <div className="adm">
      <aside className="side">
        <Logo sub="Admin portal" />
        {ADMIN_NAV.map(([to, label, icon, end]) => <NavLink key={to} to={to} end={end}><Icon name={icon} />{label}</NavLink>)}
        <div className="foot">
          <div>{user.email}</div>
          <div style={{ opacity: .7 }}>Administrator</div>
          <button onClick={logout}><Icon name="logout" />Sign out</button>
        </div>
      </aside>
      <div className="admain">
        <Banner />
        <main className="page">{children}</main>
      </div>
    </div>
  );
}

function ShopFooter() {
  return <footer className="shop-footer"><div className="footer-inner"><div><Logo sub="Smart shopping" /><p>Discover a better way to browse with catalog-aware recommendations.</p></div><div className="footer-links"><Link to="/products">Browse products</Link><Link to="/chat">AI assistant</Link><Link to="/profile">Profile</Link></div><small>SmartCart AI · Local development experience</small></div></footer>;
}

function Shell() {
  const { user, loading } = useAuth();
  const loc = useLocation();
  if (loading) return <p className="muted page">Loading…</p>;
  const adminArea = user && user.role === "admin" && loc.pathname.startsWith("/admin");
  const routes = (
    <Routes>
      <Route path="/" element={<Home />} />
      <Route path="/products" element={<Products />} />
      <Route path="/product/:id" element={<ProductDetail />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="/dashboard" element={<RequireAuth><Dashboard /></RequireAuth>} />
      <Route path="/chat" element={<RequireAuth><Chat /></RequireAuth>} />
      <Route path="/profile" element={<RequireAuth><Profile /></RequireAuth>} />
      <Route path="/admin" element={<RequireAuth admin><AdminOverview /></RequireAuth>} />
      <Route path="/admin/users" element={<RequireAuth admin><AdminUsers /></RequireAuth>} />
      <Route path="/admin/churn" element={<RequireAuth admin><AdminChurn /></RequireAuth>} />
      <Route path="/admin/models" element={<RequireAuth admin><AdminModels /></RequireAuth>} />
      <Route path="/admin/customer" element={<RequireAuth admin><AdminCustomer /></RequireAuth>} />
      <Route path="/admin/customer/:id" element={<RequireAuth admin><AdminCustomer /></RequireAuth>} />
      <Route path="/admin/audit" element={<RequireAuth admin><AdminAudit /></RequireAuth>} />
      <Route path="/admin/monitoring" element={<RequireAuth admin><AdminMonitoring /></RequireAuth>} />
      <Route path="/customer/*" element={<Navigate to="/admin/customer" replace />} />
      <Route path="/churn" element={<Navigate to="/admin/churn" replace />} />
      <Route path="*" element={<p className="page">Page not found.</p>} />
    </Routes>
  );
  return adminArea ? <AdminShell>{routes}</AdminShell> : (
    <>
      <ShopTop />
      <Banner />
      <main className="page">{routes}</main>
      <ShopFooter />
    </>
  );
}

export default function App() {
  return <AuthProvider><Shell /></AuthProvider>;
}
