import json
import logging

from .. import accounts, catalog, config, personalize
from ..appdb import new_id, now_ms
from . import intents, llm

logger = logging.getLogger(__name__)

HELP_TEXT = ("I can help you find products, show popular or similar items, recommend products based on your activity, and explain a recommendation. "
             "Try: \"Show me popular products\", \"Find headphones under $50\", or \"What should I buy based on my interests?\"")
STOCK_WORD = {1: "in stock", 0: "out of stock", None: "stock unknown"}


def money(p):
    return f"${float(p['price']):,.2f}"


def line(i, p):
    return f"{i}. {p['name']} - {money(p)}, {STOCK_WORD.get(p['in_stock'], 'stock unknown')}"


def listing(products, limit=5):
    return "\n".join(line(i + 1, p) for i, p in enumerate(products[:limit]))


def arabic_listing(products, limit=6):
    return "\n".join(f"{i}. {p['name']} - {money(p)}، {'متوفر' if p['in_stock'] else 'غير متوفر'}" for i, p in enumerate(products[:limit], 1))


def describe_filters(it):
    parts = []
    if it.product_type:
        parts.append(it.product_type.lower())
    if it.tokens:
        parts.append(" ".join(it.tokens))
    if it.department:
        parts.append(f"in {it.department}")
    if it.min_price is not None and it.max_price is not None:
        parts.append(f"between ${it.min_price:g} and ${it.max_price:g}")
    elif it.max_price is not None:
        parts.append(f"under ${it.max_price:g}")
    elif it.min_price is not None:
        parts.append(f"over ${it.min_price:g}")
    if it.in_stock:
        parts.append("in stock")
    return " ".join(parts) or "your request"


class ChatService:
    def __init__(self, con, ranker_svc, adb, provider=None):
        self.con, self.ranker, self.adb, self.provider = con, ranker_svc, adb, provider
        self.departments = catalog.departments(con)
        self.product_types = catalog.product_types(con)

    def _ctx_item(self, context_item_id):
        if context_item_id is None:
            return None
        return catalog.get_product(self.con, context_item_id) and int(context_item_id)

    def _search(self, it):
        stock = "in_stock" if it.in_stock else "any"
        kw = dict(department=it.department, product_type=it.product_type, min_price=it.min_price, max_price=it.max_price, stock=stock, limit=8)
        res = catalog.search(self.con, it.tokens, **kw)
        if res:
            return res, None
        if it.tokens:
            res = catalog.search(self.con, [], **kw) if (it.department or it.product_type or it.min_price is not None or it.max_price is not None) else []
            if res:
                return res, "relaxed"
        return [], None

    def respond(self, account, profile, message, conversation, context_item_id=None):
        it = intents.interpret(message, self.departments, self.product_types, self._ctx_item(context_item_id))
        facts = {"products": [], "notes": []}
        reply, products, source, actions, suggestions, reasons = "", [], "catalog", [], [], {}
        if it.intent == "help":
            reply = HELP_TEXT
            suggestions = ["Show me popular products", "What should I buy based on my interests?", "I'm a new user. Help me discover products."]
        elif it.intent == "popular":
            products = catalog.popular(self.con, 8, departments=[it.department] if it.department else None, min_price=it.min_price, max_price=it.max_price)
            source = "popularity"
            if it.language == "ar":
                reply = ("هذه بعض المنتجات الشائعة" + (f" في قسم {it.department}" if it.department else "") + " بناءً على نشاط الكتالوج:\n" + arabic_listing(products)) if products \
                    else "لم أجد منتجات شائعة لهذا الطلب."
            else:
                reply = ("Here are popular products" + (f" in {it.department}" if it.department else "") + " from the shop's recent activity:\n" + listing(products)) if products \
                    else "I could not find popular products for that request."
        elif it.intent == "recommend":
            if it.tokens or it.department or it.product_type or it.min_price is not None or it.max_price is not None:
                products, relaxed = self._search(it)
                source = "catalog_search"
            else:
                products = catalog.popular(self.con, 6)
                source = "catalog_recommendation"
            reasons = {p["item_id"]: ("اختيار من المنتجات المتاحة ذات النشاط الأعلى في الكتالوج" if it.language == "ar" else "Selected from available products with stronger catalog activity") for p in products}
            if products:
                if it.language == "ar":
                    reply = "هذه ترشيحات من كتالوج SmartCart:\n" + arabic_listing(products) + "\nالسبب: اخترتها لأنها متاحة في الكتالوج ولها نشاط موثق؛ أخبرني بالقسم أو الميزانية لأضيق الاختيارات."
                else:
                    reply = "Here are catalog-grounded recommendations:\n" + listing(products) + "\nWhy these? They are available catalog records with stronger recorded activity. Tell me a department or budget and I can narrow the choices."
            else:
                reply = ("لم أجد منتجات تطابق طلبك. جرّب تحديد قسم أو ميزانية مختلفة." if it.language == "ar" else "I could not find products matching that request. Try a department or a different budget.")
                suggestions = [f"Show me {d}" for d in self.departments[:3]]
        elif it.intent == "discover":
            prefs = accounts.get_preferences(self.adb, account["id"])
            products = catalog.popular(self.con, 6, departments=prefs or None)
            source = "preference_based" if prefs and products else "popularity"
            intro = ("You chose " + ", ".join(prefs) + ", so these are popular there:\n") if prefs else "Welcome! I do not know your interests yet, so these are popular products to start with:\n"
            reply = intro + listing(products) + "\nTell me what you like, for example a department or a type of product, and I will search for it."
            if not prefs:
                actions = [{"label": "Choose your interests", "to": "/profile"}]
            suggestions = [f"Show me {d}" for d in self.departments[:3]]
        elif it.intent == "personal":
            profile_ = profile
            hist = personalize.history_frame(self.con, self.adb, account["id"], profile_)
            prefs = accounts.get_preferences(self.adb, account["id"])
            products, source = personalize.recommended(self.con, self.ranker, hist, prefs, 6)
            reasons = {p["item_id"]: p.get("reason", "") for p in products}
            if source == "history_based":
                reply = "Based on your activity, here is what I would suggest:\n" + listing(products)
            elif source == "preference_based":
                reply = "You have no activity yet, so these are popular products in the departments you chose (" + ", ".join(prefs) + "):\n" + listing(products)
            else:
                reply = "I have no history or interests for you yet, so these are simply popular products, not personal picks:\n" + listing(products)
                actions = [{"label": "Choose your interests", "to": "/profile"}]
        elif it.intent == "similar":
            item = it.item_id
            if item is None and it.tokens:
                found = catalog.search(self.con, it.tokens, department=it.department, product_type=it.product_type, limit=1)
                item = found[0]["item_id"] if found else None
            base = catalog.get_product(self.con, item) if item is not None else None
            if base is None:
                reply = "Which product do you mean? Open a product page and ask again from there, or give me its name."
            else:
                products = catalog.similar(self.con, base["item_id"], 6)
                source = "item_similarity"
                if products:
                    reply = f"Products that shoppers often look at together with {base['name']}:\n" + listing(products)
                    reasons = {p["item_id"]: f"Looked at in the same visit as {base['name']}." for p in products}
                else:
                    reply = f"I have no similarity data for {base['name']}."
        elif it.intent == "details":
            item = it.item_id
            if item is None and (it.tokens or it.product_type):
                found = catalog.search(self.con, it.tokens, department=it.department, product_type=it.product_type, limit=1)
                item = found[0]["item_id"] if found else None
            p = catalog.get_product(self.con, item) if item is not None else None
            if p is None:
                reply = "I could not find that product in the catalog. Try its name or open its page and ask from there."
            else:
                products = [p]
                deal = " It is priced well below similar products." if p["is_deal"] else ""
                reply = f"{p['name']} by {p['brand'] if 'brand' in p and p['brand'] else 'an unknown brand'} is a {p['product_type'].lower()} in {p['department']}, priced at {money(p)} and {STOCK_WORD.get(p['in_stock'])}.{deal}"
        elif it.intent == "why":
            last = self.adb.one("SELECT meta, product_ids FROM chat_messages WHERE conversation_id = ? AND role = 'assistant' AND product_ids <> '[]' ORDER BY created_at DESC LIMIT 1",
                                (conversation["id"],)) if conversation else None
            if last is None:
                reply = "I have not recommended anything in this conversation yet. Ask me to recommend something first, then ask why."
            else:
                ids = json.loads(last["product_ids"])
                meta = json.loads(last["meta"])
                info = catalog.get_products(self.con, ids)
                products = [info[i] for i in ids if i in info]
                stored = meta.get("reasons", {})
                lines = [f"{p['name']}: {stored.get(str(p['item_id'])) or 'it matched your search, I have no further reason stored.'}" for p in products]
                reply = "Here is why each product was suggested:\n" + "\n".join(lines)
                source = meta.get("source", "catalog")
        else:
            products, relaxed = self._search(it)
            what = describe_filters(it)
            if products and relaxed:
                reply = f"I found nothing matching \"{' '.join(it.tokens)}\", so here are products that fit the rest of your request ({what.replace(' '.join(it.tokens), '').strip()}):\n" + listing(products)
            elif products:
                reply = f"I found {len(products)} product(s) for {what}:\n" + listing(products)
            else:
                reply = f"I could not find products for {what}. Try fewer words, another department, or a different price range."
                suggestions = [f"Show me {d}" for d in self.departments[:3]]
        facts["products"] = [{"item_id": p["item_id"], "name": p["name"], "price": float(p["price"]), "in_stock": p["in_stock"], "department": p["department"]} for p in products[:6]]
        facts["notes"] = [f"source: {source}", f"intent: {it.intent}"]
        used_llm = False
        if self.provider is not None and it.intent not in ("help",):
            try:
                payload = json.dumps({"user_message": it.text[:config.CHAT_MAX_CHARS], "language": it.language, "intent": it.intent, "facts": {**facts, "recommendation_reasons": reasons}, "deterministic_reply": reply}, ensure_ascii=False)
                raw = self.provider.complete(llm.SYSTEM_PROMPT, payload)
                extra = [x for x in (it.min_price, it.max_price) if x is not None]
                msg, ids = llm.validate_output(raw, facts["products"], extra)
                reply, used_llm = msg, True
                if ids:
                    order = {i: n for n, i in enumerate(ids)}
                    products = sorted([p for p in products if p["item_id"] in order], key=lambda p: order[p["item_id"]])
            except llm.LLMError as exc:
                # The deterministic catalog answer remains the safe fallback. The
                # reason is diagnostic metadata only and never includes provider text.
                logger.warning("llm_fallback reason=%s", exc.code)
        return {"reply": reply, "products": products[:8], "intent": it.intent, "source": source, "used_llm": used_llm, "actions": actions,
                "suggestions": suggestions, "reasons": {str(k): v for k, v in reasons.items()}}


def get_conversation(adb, account_id, conversation_id):
    return adb.one("SELECT * FROM chat_conversations WHERE id = ? AND account_id = ?", (conversation_id, account_id))


def handle_chat(svc, account, profile, message, conversation_id=None, context_item_id=None):
    adb = svc.adb
    conv = get_conversation(adb, account["id"], conversation_id) if conversation_id else None
    if conversation_id and conv is None:
        return None
    result = svc.respond(account, profile, message, conv, context_item_id)
    ts = now_ms()
    with adb.transaction():
        if conv is None:
            conv = {"id": new_id()}
            adb.execute("INSERT INTO chat_conversations (id, account_id, title, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                        (conv["id"], account["id"], " ".join(message.split())[:60], ts, ts))
        adb.execute("INSERT INTO chat_messages (id, conversation_id, role, content, product_ids, meta, created_at) VALUES (?, ?, 'user', ?, '[]', '{}', ?)",
                    (new_id(), conv["id"], message, ts))
        adb.execute("INSERT INTO chat_messages (id, conversation_id, role, content, product_ids, meta, created_at) VALUES (?, ?, 'assistant', ?, ?, ?, ?)",
                    (new_id(), conv["id"], result["reply"], json.dumps([p["item_id"] for p in result["products"]]),
                     json.dumps({"intent": result["intent"], "source": result["source"], "reasons": result["reasons"], "used_llm": result["used_llm"]}), ts + 1))
        adb.execute("UPDATE chat_conversations SET updated_at = ? WHERE id = ?", (ts + 1, conv["id"]))
    result["conversation_id"] = conv["id"]
    result.pop("reasons", None)
    return result
