"""LLM_SEED / LLM_TEMPERATURE reach the OpenAI-compatible payload (Ollama /v1 reads "seed")."""

from __future__ import annotations

import json

import httpx
import pytest

from app.core.config import Settings
from app.llm.models import LLMMessage
from app.llm.registry import LLMProviderRegistry


def _settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "_env_file": None,
        "llm_enabled": True,
        "llm_provider": "ollama",
        "llm_ollama_model": "qwen2.5:3b",
        "llm_ollama_num_ctx": 8192,
    }
    values.update(overrides)
    return Settings(**values)


async def _payload(settings: Settings, *, temperature: float) -> dict[str, object]:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured.update(json.loads(request.read().decode()))
        return httpx.Response(
            200,
            json={
                "model": "qwen2.5:3b",
                "choices": [{"message": {"content": "OK"}, "finish_reason": "stop"}],
            },
        )

    provider = LLMProviderRegistry(
        settings, transport=httpx.MockTransport(handler)
    ).create_provider()
    await provider.generate(
        messages=(LLMMessage(role="user", content="Say OK"),),
        temperature=temperature,
        max_output_tokens=16,
    )
    return captured


@pytest.mark.anyio
async def test_ollama_payload_carries_seed_and_temperature() -> None:
    payload = await _payload(_settings(llm_seed=20261031), temperature=0.0)

    assert payload["seed"] == 20261031
    assert payload["temperature"] == 0.0
    assert payload["options"] == {"num_ctx": 8192, "seed": 20261031}


@pytest.mark.anyio
async def test_unset_seed_is_not_sent() -> None:
    payload = await _payload(_settings(), temperature=0.0)

    assert "seed" not in payload
    assert payload["options"] == {"num_ctx": 8192}


@pytest.mark.anyio
async def test_openai_compatible_provider_sends_seed_without_ollama_options() -> None:
    settings = _settings(
        llm_provider="openai_compatible",
        llm_base_url="http://localhost:8001/v1",
        llm_model="local-model",
        llm_seed=7,
    )
    payload = await _payload(settings, temperature=0.2)

    assert payload["seed"] == 7
    assert payload["temperature"] == 0.2
    assert "options" not in payload


def test_seed_setting_parsing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("LLM_SEED", "")
    assert Settings(_env_file=None).llm_seed is None
    monkeypatch.setenv("LLM_SEED", "42")
    assert Settings(_env_file=None).llm_seed == 42
    monkeypatch.delenv("LLM_SEED")
    with pytest.raises(ValueError):
        Settings(_env_file=None, llm_seed=True)
    with pytest.raises(ValueError):
        Settings(_env_file=None, llm_seed=-1)
