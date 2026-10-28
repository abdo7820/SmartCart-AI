import { useEffect, useRef, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { del, get, post } from "../api";
import { Grid, ProductCard } from "../components.jsx";

const START = ["Show me popular products", "Recommend something for me", "Find a gift under 50"];

export default function Chat() {
  const [sp] = useSearchParams();
  const initialQ = sp.get("q");
  const ctx = sp.get("item") ? Number(sp.get("item")) : null;
  const [msgs, setMsgs] = useState([]);
  const [convId, setConvId] = useState(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [retry, setRetry] = useState(null);
  const [suggestions, setSuggestions] = useState(START);
  const [convs, setConvs] = useState([]);
  const end = useRef(null);

  const loadList = () => get("/chat/conversations").then(setConvs).catch(() => {});
  useEffect(() => { loadList(); }, []);
  const sentInitial = useRef(false);
  useEffect(() => {
    if (initialQ && !sentInitial.current) { sentInitial.current = true; send(initialQ); }
  }, []);
  useEffect(() => { end.current && end.current.scrollIntoView({ block: "end" }); }, [msgs, busy]);

  const open = async (id) => {
    setError("");
    try {
      const c = await get(`/chat/conversations/${id}`);
      setConvId(id);
      setMsgs(c.messages.map((m) => ({ role: m.role, text: m.content, products: m.products })));
      setSuggestions([]);
    } catch (e) { setError(e.message); }
  };
  const fresh = () => { setConvId(null); setMsgs([]); setSuggestions(START); setError(""); };
  const remove = async (id) => {
    await del(`/chat/conversations/${id}`);
    if (id === convId) fresh();
    loadList();
  };

  const send = async (message, useCtx = false, appendUser = true) => {
    const m = message.trim();
    if (!m || busy) return;
    setBusy(true);
    setError("");
    setRetry(null);
    if (appendUser) setMsgs((x) => [...x, { role: "user", text: m }]);
    setText("");
    try {
      const body = { message: m };
      if (convId) body.conversation_id = convId;
      if (useCtx && ctx !== null) body.context_item_id = ctx;
      const res = await post("/chat", body);
      setConvId(res.conversation_id);
      setMsgs((x) => [...x, { role: "assistant", text: res.reply, products: res.products, reasons: res.reasons, actions: res.actions, source: res.source, usedLlm: res.used_llm }]);
      setSuggestions(res.suggestions || []);
      loadList();
    } catch (e) {
      setError(e.message);
      setRetry({ message: m, useCtx });
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="chatlayout">
      <aside className="card convs">
        <button onClick={fresh}>New chat</button>
        <ul>
          {convs.map((c) => (
            <li key={c.id} className={c.id === convId ? "on" : ""}>
              <button className="link" onClick={() => open(c.id)}>{c.title || "Conversation"}</button>
              <button className="ghost x" onClick={() => remove(c.id)} aria-label={`Delete ${c.title || "conversation"}`}>×</button>
            </li>
          ))}
          {convs.length === 0 && <li className="muted small">No saved chats</li>}
        </ul>
      </aside>
      <section className="chat">
        <h1>AI shopping assistant</h1>
        <p className="muted small">It answers from this shop's catalog and your recommendations only. Replies are checked against real products and prices.</p>
        {ctx !== null && <p className="card notice small">Asking about product #{ctx}. <button className="ghost" onClick={() => send("Tell me about this product", true)}>Ask about it</button></p>}
        <div className="log" role="log" aria-live="polite">
          {msgs.length === 0 && <p className="muted">Ask for products, deals, gifts or recommendations.</p>}
          {msgs.map((m, i) => (
            <div key={i} className={`bubble ${m.role}`}>
              <div className="text">{m.text}</div>
              {m.products && m.products.length > 0 && (
                <Grid>{m.products.map((p) => <ProductCard key={p.item_id} p={p} note={m.reasons && m.reasons[p.item_id]} />)}</Grid>
              )}
              {m.actions && m.actions.map((a) => <Link key={a.to} className="btn" to={a.to}>{a.label}</Link>)}
              {m.role === "assistant" && m.source && <div className="muted small">{m.usedLlm ? "Written by the AI model, checked against the catalog" : "Answered from the catalog"}</div>}
            </div>
          ))}
          {busy && <div className="bubble assistant muted">Thinking…</div>}
          <div ref={end} />
        </div>
        {error && <div className="error chat-error" role="alert"><span>{error}</span>{retry && <button type="button" className="ghost" onClick={() => send(retry.message, retry.useCtx, false)} disabled={busy}>Retry</button>}</div>}
        <div className="chips">{suggestions.map((s) => <button key={s} className="ghost" disabled={busy} onClick={() => send(s)}>{s}</button>)}</div>
        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(text); }}>
          <textarea value={text} maxLength={500} rows={1} onChange={(e) => setText(e.target.value)} onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(text); } }} placeholder="Ask about products, gifts, or recommendations" aria-label="Message" />
          <button type="submit" disabled={busy || !text.trim()}>Send</button>
        </form>
      </section>
    </div>
  );
}
