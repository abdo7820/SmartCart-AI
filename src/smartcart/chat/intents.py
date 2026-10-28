import re
from dataclasses import dataclass, field

STOPWORDS = set("""a an the me my show find recommend recommendation recommendations suggest something some any products product items item for to from under below over above than
less more i want need looking look please can could you give get with and or of in on buy what should based interests interest new user help discover popular trending
similar like this that one them cheap cheaper expensive best top is are do does have has about tell details info price prices how much cost costs between at least most max
maximum min minimum up within available stock instock stocks there here would which show-me thanks thank hi hello hey just also very really good great nice choose pick catalog""".split())
ARABIC_STOPWORDS = set("""ساعدني ساعد أساعدني أساعد اختار اختر اختيار منتج منتجات المنتج المنتجات منتجا منتجة المنتجات مناسب مناسبة مناسبا مناسبه كتالوج كتالوجي اعرض واعرض عرض أظهر أظهرلي المتاحة المتاح فعلياً فعليا الفعلية أسعارها اسعارها سعر أسعار اشرح واشرح شرح سبب ترشيحك ترشيح رشح رشحي توصية توصيات اقترح أو و من في عن على مع إلى هذا هذه ذلك تلك لي ليّ أنا أريد اريد أحتاج احتاج ابحث أبحث بحث أظهر لي موجودة موجود المتوفر المتوفرة كيف ماذا ما هل لل للمنتج لكل""".split())
BRAND_WORDS = {"smartcart", "smartcartai", "smartcart-ai", "سمارتكارت", "سمارت", "كارت"}
DEPT_WORDS = {
    "electronics": "Electronics", "electronic": "Electronics", "fashion": "Fashion", "clothes": "Fashion", "clothing": "Fashion", "beauty": "Beauty & Health",
    "health": "Beauty & Health", "toys": "Toys & Games", "toy": "Toys & Games", "games": "Toys & Games", "sports": "Sports & Outdoors", "sport": "Sports & Outdoors",
    "outdoor": "Sports & Outdoors", "outdoors": "Sports & Outdoors", "pet": "Pet Supplies", "pets": "Pet Supplies", "kitchen": "Home & Kitchen", "home": "Home & Kitchen",
    "automotive": "Automotive", "car": "Automotive", "garden": "Garden & Tools", "tools": "Garden & Tools", "books": "Books & Media", "media": "Books & Media",
    "إلكترونيات": "Electronics", "الكترونيات": "Electronics", "إلكتروني": "Electronics", "إلكترونية": "Electronics",
    "أزياء": "Fashion", "ازياء": "Fashion", "ملابس": "Fashion", "جمال": "Beauty & Health", "صحة": "Beauty & Health",
    "ألعاب": "Toys & Games", "العاب": "Toys & Games", "رياضة": "Sports & Outdoors", "رياضية": "Sports & Outdoors",
    "حيوانات": "Pet Supplies", "حيوان": "Pet Supplies", "حيوانات أليفة": "Pet Supplies", "مطبخ": "Home & Kitchen", "منزل": "Home & Kitchen",
    "سيارات": "Automotive", "سيارة": "Automotive", "حديقة": "Garden & Tools", "أدوات": "Garden & Tools", "كتب": "Books & Media",
}
NUM = r"\$?\s?(\d+(?:\.\d+)?)"


@dataclass
class Interpretation:
    intent: str
    tokens: list = field(default_factory=list)
    department: str | None = None
    product_type: str | None = None
    min_price: float | None = None
    max_price: float | None = None
    in_stock: bool = False
    item_id: int | None = None
    text: str = ""
    language: str = "en"


def stem(w):
    if len(w) > 4 and w.endswith("ies"):
        return w[:-3] + "y"
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def normalize_text(text):
    # Remove Arabic diacritics and normalize common alef variants for matching.
    text = re.sub(r"[\u064B-\u065F\u0670]", "", text)
    return text.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا").replace("ى", "ي")


def _prices(t):
    lo = hi = None
    m = re.search(r"between\s+" + NUM + r"\s*(?:and|to|-)\s*" + NUM, t)
    if m:
        a, b = float(m.group(1)), float(m.group(2))
        return min(a, b), max(a, b), t[:m.start()] + " " + t[m.end():]
    m = re.search(r"(?:under|below|less than|cheaper than|up to|at most|max(?:imum)?(?: of)?|within|<=?|تحت|اقل من|أقل من|لا تتجاوز|حتى|بميزانية)\s*" + NUM, t)
    if m:
        hi = float(m.group(1))
        t = t[:m.start()] + " " + t[m.end():]
    m = re.search(r"(?:over|above|more than|at least|min(?:imum)?(?: of)?|>=?|فوق|اكثر من|أكثر من|على الاقل|على الأقل)\s*" + NUM, t)
    if m:
        lo = float(m.group(1))
        t = t[:m.start()] + " " + t[m.end():]
    return lo, hi, t


def interpret(message, departments, product_types, context_item_id=None):
    text = re.sub(r"[\x00-\x1f]", " ", message).strip()
    low = normalize_text(text.lower())
    is_arabic = bool(re.search(r"[\u0600-\u06FF]", text))
    it = Interpretation(intent="unknown", text=text, language="ar" if is_arabic else "en")
    if not low:
        it.intent = "help"
        return it
    m = re.search(r"#(\d{1,9})\b", low) or re.search(r"\b(?:item|product)\s+(\d{1,9})\b", low) or re.search(r"\b[a-z]{2}-(\d{1,9})\b", low)
    if m:
        it.item_id = int(m.group(1))
        low = low.replace(m.group(0), " ")
    it.min_price, it.max_price, rest = _prices(low)
    if re.search(r"\b(in stock|available|instock)\b", rest):
        it.in_stock = True
    for d_word, dept in sorted(DEPT_WORDS.items(), key=lambda x: len(x[0]), reverse=True):
        if re.search(rf"\b{d_word}\b", rest) and dept in departments:
            it.department = dept
            rest = re.sub(rf"\b{d_word}\b", " ", rest)
            break
    for pt in sorted(product_types, key=len, reverse=True):
        pl = pt.lower()
        pat = r"\b" + r"\s+".join(re.escape(w) for w in pl.split()) + r"s?\b"
        if re.search(pat, rest):
            it.product_type = pt
            rest = re.sub(pat, " ", rest)
            break
    # Application/brand names are context, never product search terms.
    rest = re.sub(r"\bsmartcart(?:\s+ai)?\b", " ", rest, flags=re.I)
    rest = re.sub(r"سمارت\s*كارت", " ", rest)
    words = re.findall(r"[a-z][a-z'-]+|[\u0600-\u06FF]+", rest)
    it.tokens = [stem(w) for w in words if w not in STOPWORDS and w not in ARABIC_STOPWORDS and w not in BRAND_WORDS and len(w) > 1]
    has_slots = bool(it.tokens or it.department or it.product_type or it.min_price is not None or it.max_price is not None)
    general_shopping = bool(re.search(r"\b(help me choose|help me pick|recommend(?: something| a product)?|suggest(?: something| a product)?|what should i buy|find something for me)\b", low)
                             or re.search(r"(ساعدني|ساعد|اختار|اختيار|رشح|ترشيح|توصية|اقترح|منتج مناسب|ماذا اشتري|ماذا أشتري)", low))
    if re.search(r"\bwhy\b", low) and re.search(r"\b(recommend|suggest|show|these|those|this)\w*", low):
        it.intent = "why"
    elif re.search(r"\b(similar|like this|alternatives?|related to|more like|same as)\b", low):
        it.intent = "similar"
        if it.item_id is None and context_item_id is not None and not it.tokens and not it.product_type:
            it.item_id = context_item_id
    elif re.search(r"\b(for me|my interests|my taste|what should i (buy|get)|based on (my|what i)|personali[sz]ed|my history)\b", low):
        it.intent = "personal"
    elif re.search(r"\b(new user|just joined|first time|help me discover|discover|where (do|should) i start)\b", low):
        it.intent = "discover"
    elif re.search(r"\b(popular|trending|best[- ]?sell\w*|top (selling|products|items)|most bought)\b", low):
        it.intent = "popular"
    elif general_shopping:
        it.intent = "recommend"
    elif re.search(r"\b(tell me about|details?|more info|price of|how much|is (it|this) in stock|specs?)\b", low):
        it.intent = "details"
        if it.item_id is None and context_item_id is not None and not it.tokens:
            it.item_id = context_item_id
    elif re.match(r"^\s*(hi|hello|hey|help|what can you do|who are you)\b", low) and not has_slots:
        it.intent = "help"
    elif has_slots or it.item_id is not None:
        it.intent = "search"
    else:
        it.intent = "help"
    return it
