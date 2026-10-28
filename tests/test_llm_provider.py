import httpx
import pytest

from smartcart.chat import llm


def response(status, payload):
    return httpx.Response(status, json=payload, request=httpx.Request("POST", "https://example.test/chat/completions"))


def test_groq_openai_compatible_provider_uses_configured_model_and_endpoint(monkeypatch):
    calls = []

    def fake_post(url, **kwargs):
        calls.append((url, kwargs))
        return response(200, {"choices": [{"message": {"content": '{"message":"ok","product_ids":[]}'}}]})

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    provider = llm.OpenAICompatibleProvider("new-key", "llama-3.3-70b-versatile", "https://api.groq.com/openai/v1")
    assert provider.complete("system", "user")
    assert calls[0][0] == "https://api.groq.com/openai/v1/chat/completions"
    assert calls[0][1]["headers"]["authorization"] == "Bearer new-key"
    assert calls[0][1]["json"]["model"] == "llama-3.3-70b-versatile"


@pytest.mark.parametrize(("status", "code"), [(401, "invalid_credentials"), (404, "model_or_endpoint_not_found"), (429, "provider_rate_limited"), (503, "provider_unavailable")])
def test_provider_errors_are_classified_without_provider_body(monkeypatch, status, code):
    monkeypatch.setattr(llm.httpx, "post", lambda *args, **kwargs: response(status, {"error": {"message": "secret provider detail"}}))
    provider = llm.OpenAICompatibleProvider("key", "model", "https://example.test/v1")
    with pytest.raises(llm.LLMError) as exc:
        provider.complete("system", "user")
    assert exc.value.code == code
    assert "secret" not in str(exc.value)


def test_provider_timeout_is_safe(monkeypatch):
    def timeout(*args, **kwargs):
        raise httpx.ReadTimeout("provider timed out")

    monkeypatch.setattr(llm.httpx, "post", timeout)
    with pytest.raises(llm.LLMError) as exc:
        llm.OpenAICompatibleProvider("key", "model").complete("system", "user")
    assert exc.value.code == "timeout"


def test_provider_from_config_supports_groq_without_exposing_key(monkeypatch):
    from smartcart import config

    monkeypatch.setattr(config, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(config, "LLM_API_KEY", "rotated-key")
    monkeypatch.setattr(config, "LLM_MODEL", "llama-3.3-70b-versatile")
    monkeypatch.setattr(config, "LLM_BASE_URL", "https://api.groq.com/openai/v1")
    provider = llm.provider_from_config()
    assert provider.name == "openai"
    assert provider.model == "llama-3.3-70b-versatile"
    assert provider.base == "https://api.groq.com/openai/v1"


def test_missing_provider_configuration_returns_deterministic_mode(monkeypatch):
    from smartcart import config

    monkeypatch.setattr(config, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(config, "LLM_API_KEY", None)
    monkeypatch.setattr(config, "LLM_MODEL", "llama-3.3-70b-versatile")
    assert llm.provider_from_config() is None
