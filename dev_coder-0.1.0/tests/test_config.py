import os
import pytest
from agent.config import load_config


def test_load_config_from_env(monkeypatch):
    monkeypatch.setenv("OPENAI_BASE_URL", "https://custom-endpoint/v1")
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
    monkeypatch.setenv("OPENAI_MODEL", "custom-model")

    config = load_config()
    assert config.base_url == "https://custom-endpoint/v1"
    assert config.api_key == "test-key-123"
    assert config.model == "custom-model"


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("OPENAI_BASE_URL", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_MODEL", raising=False)

    config = load_config()
    assert config.base_url is not None
    assert config.api_key is not None
    assert config.model is not None
