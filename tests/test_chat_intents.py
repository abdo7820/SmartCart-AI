import json

from smartcart import db
from smartcart.chat import intents, llm, service


DEPARTMENTS = ["Electronics", "Fashion", "Toys & Games", "Home & Kitchen"]
PRODUCT_TYPES = ["Watch", "Speaker", "Jacket"]


def test_arabic_general_shopping_request_is_not_a_smartcart_search():
    message = "ساعدني أختار منتجًا مناسبًا من كتالوج SmartCart، واعرض المنتجات المتاحة مع أسعارها الفعلية واشرح سبب ترشيحك لكل منتج."
    result = intents.interpret(message, DEPARTMENTS, PRODUCT_TYPES)
    assert result.intent == "recommend"
    assert result.language == "ar"
    assert result.tokens == []


def test_english_general_shopping_request_is_recommendation():
    result = intents.interpret("Help me choose a product from the SmartCart catalog", DEPARTMENTS, PRODUCT_TYPES)
    assert result.intent == "recommend"
    assert result.tokens == []


def test_explicit_category_and_budget_are_preserved():
    result = intents.interpret("Recommend fashion under $40", DEPARTMENTS, PRODUCT_TYPES)
    assert result.intent == "recommend"
    assert result.department == "Fashion"
    assert result.max_price == 40


def test_unmatched_keyword_remains_a_real_search():
    result = intents.interpret("Find a nonexistent unicorn gadget", DEPARTMENTS, PRODUCT_TYPES)
    assert result.intent == "search"
    assert "unicorn" in result.tokens


class FakeADB:
    def one(self, *args, **kwargs):
        return None


class FakeProvider(llm.LLMProvider):
    name = "openai"

    def __init__(self, fail=False):
        self.payload = None
        self.fail = fail

    def complete(self, system, user):
        if self.fail:
            raise llm.LLMError("provider_unavailable")
        self.payload = json.loads(user)
        product = self.payload["facts"]["products"][0]
        return json.dumps({"message": f"A verified catalog choice: {product['name']} for ${product['price']:.2f}.", "product_ids": [product["item_id"]]})


def test_general_recommendation_uses_real_catalog_records_and_groq_rewriter():
    con = db.connect()
    provider = FakeProvider()
    try:
        svc = service.ChatService(con, None, FakeADB(), provider)
        result = svc.respond({"id": "test-account"}, {}, "Help me choose a product from the SmartCart catalog", None)
        assert result["intent"] == "recommend"
        assert result["used_llm"] is True
        assert result["products"]
        assert result["products"][0]["item_id"] == provider.payload["facts"]["products"][0]["item_id"]
        assert result["products"][0]["name"] in result["reply"]
    finally:
        con.close()


def test_provider_failure_keeps_catalog_grounded_fallback():
    con = db.connect()
    try:
        svc = service.ChatService(con, None, FakeADB(), FakeProvider(fail=True))
        result = svc.respond({"id": "test-account"}, {}, "ساعدني أختار منتجًا من SmartCart", None)
        assert result["intent"] == "recommend"
        assert result["used_llm"] is False
        assert result["products"]
        assert result["products"][0]["name"] in result["reply"]
    finally:
        con.close()
