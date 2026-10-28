"""Safely verify the configured OpenAI-compatible model without printing secrets."""

import sys
from pathlib import Path

import httpx

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from smartcart import config  # noqa: E402


def main():
    provider = config.LLM_PROVIDER
    if provider in ("none", ""):
        print("LLM_PROVIDER=none; deterministic catalog assistant is active")
        return 0
    if provider not in ("openai", "openai-compatible"):
        print(f"Unsupported provider: {provider}")
        return 2
    if not config.LLM_API_KEY or not config.LLM_MODEL:
        print("Provider is configured but LLM_API_KEY or LLM_MODEL is missing")
        return 2
    base = (config.LLM_BASE_URL or "https://api.openai.com/v1").rstrip("/")
    try:
        response = httpx.get(f"{base}/models", headers={"authorization": f"Bearer {config.LLM_API_KEY}"}, timeout=config.LLM_TIMEOUT_S)
        if response.status_code != 200:
            print(f"Provider model check failed: HTTP {response.status_code}")
            return 1
        models = response.json().get("data", [])
        ids = {m.get("id") for m in models if isinstance(m, dict)}
        if config.LLM_MODEL not in ids:
            print(f"Configured model is not listed by the provider: {config.LLM_MODEL}")
            return 1
        print(f"Provider reachable; configured model is available: {config.LLM_MODEL}")
        return 0
    except httpx.TimeoutException:
        print("Provider model check timed out")
        return 1
    except (httpx.HTTPError, ValueError, TypeError, AttributeError):
        print("Provider model check failed due to a network or response error")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
