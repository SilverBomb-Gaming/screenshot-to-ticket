"""Provider settings: defaults, overrides, and the opt-in endpoint."""

from __future__ import annotations

import pytest

from shot_ticket.config import (
    DEFAULT_OLLAMA_BASE_URL,
    DEFAULT_OLLAMA_MODEL,
    DEFAULT_OPENAI_BASE_URL,
    ConfigError,
    resolve_settings,
)


def test_ollama_defaults():
    settings = resolve_settings(env={})
    assert settings.provider == "ollama"
    assert settings.model == DEFAULT_OLLAMA_MODEL == "llava"
    assert settings.base_url == DEFAULT_OLLAMA_BASE_URL
    assert settings.api_key is None
    assert settings.json_mode is True
    assert settings.timeout == 180


def test_cli_overrides_environment():
    settings = resolve_settings(
        provider="ollama",
        model="llama3.2-vision",
        base_url="http://localhost:11434/",
        env={
            "SHOT_TICKET_MODEL": "llava",
            "SHOT_TICKET_BASE_URL": "http://example.invalid",
            "SHOT_TICKET_API_KEY": "secret",
        },
    )
    assert settings.model == "llama3.2-vision"
    assert settings.base_url == "http://localhost:11434"
    assert settings.api_key == "secret"


def test_openai_requires_a_model_and_defaults_the_base_url():
    with pytest.raises(ConfigError, match="SHOT_TICKET_MODEL"):
        resolve_settings(provider="openai", env={})
    settings = resolve_settings(
        provider="openai",
        model="gpt-4o",
        env={"SHOT_TICKET_API_KEY": "  sk-test  "},
    )
    assert settings.base_url == DEFAULT_OPENAI_BASE_URL
    assert settings.api_key == "sk-test"
    assert settings.model == "gpt-4o"


def test_bad_provider_timeout_and_json_mode():
    with pytest.raises(ConfigError, match="ollama"):
        resolve_settings(provider="azure", env={})
    with pytest.raises(ConfigError, match="SHOT_TICKET_TIMEOUT"):
        resolve_settings(env={"SHOT_TICKET_TIMEOUT": "soon"})
    with pytest.raises(ConfigError, match="positive"):
        resolve_settings(env={"SHOT_TICKET_TIMEOUT": "0"})
    with pytest.raises(ConfigError, match="SHOT_TICKET_JSON_MODE"):
        resolve_settings(env={"SHOT_TICKET_JSON_MODE": "maybe"})
    assert resolve_settings(env={"SHOT_TICKET_JSON_MODE": "off"}).json_mode is False
