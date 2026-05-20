import pytest

from src import config
from src.config import resolve_config

_ENV_VARS = [
    "CORAS_TEXTGEN_API_BASE",
    "CORAS_TEXTGEN_API_KEY",
    "CORAS_TEXTGEN_MODEL",
    "CORAS_TEXTGEN_SYSTEM_PROMPT",
    "CORAS_TEXTGEN_TEMPERATURE",
    "CORAS_TEXTGEN_TIMEOUT",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Isolate each test: no env vars and an empty settings file by default."""
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(config, "_load_settings", lambda: {})


def set_settings(monkeypatch, data):
    monkeypatch.setattr(config, "_load_settings", lambda: data)


def test_missing_api_key_raises(monkeypatch):
    with pytest.raises(ValueError, match="No API key"):
        resolve_config()


def test_defaults_with_key_from_env(monkeypatch):
    monkeypatch.setenv("CORAS_TEXTGEN_API_KEY", "k")
    cfg = resolve_config()
    assert cfg.api_base == "https://api.openai.com/v1"
    assert cfg.model == "gpt-4o-mini"
    assert cfg.system_prompt == "You are a helpful assistant."
    assert cfg.temperature == 0.7
    assert cfg.timeout == 60.0


def test_settings_override_env(monkeypatch):
    monkeypatch.setenv("CORAS_TEXTGEN_API_KEY", "env-key")
    monkeypatch.setenv("CORAS_TEXTGEN_MODEL", "env-model")
    set_settings(
        monkeypatch,
        {
            "coras_textgen.apiKey": "settings-key",
            "coras_textgen.model": "settings-model",
        },
    )
    cfg = resolve_config()
    assert cfg.api_key == "settings-key"
    assert cfg.model == "settings-model"


def test_node_override_beats_settings(monkeypatch):
    set_settings(
        monkeypatch,
        {
            "coras_textgen.apiKey": "k",
            "coras_textgen.model": "settings-model",
            "coras_textgen.systemPrompt": "settings prompt",
        },
    )
    cfg = resolve_config(system_prompt_override="node prompt", model_override="node-model")
    assert cfg.model == "node-model"
    assert cfg.system_prompt == "node prompt"


def test_blank_override_falls_back(monkeypatch):
    set_settings(
        monkeypatch,
        {"coras_textgen.apiKey": "k", "coras_textgen.model": "settings-model"},
    )
    cfg = resolve_config(model_override="   ")
    assert cfg.model == "settings-model"


def test_api_base_trailing_slash_stripped(monkeypatch):
    set_settings(
        monkeypatch,
        {"coras_textgen.apiKey": "k", "coras_textgen.apiBase": "https://host/v1/"},
    )
    assert resolve_config().api_base == "https://host/v1"


def test_numeric_from_settings_and_env(monkeypatch):
    set_settings(
        monkeypatch,
        {
            "coras_textgen.apiKey": "k",
            "coras_textgen.temperature": 0.2,
            "coras_textgen.timeout": 15,
        },
    )
    cfg = resolve_config()
    assert cfg.temperature == 0.2
    assert cfg.timeout == 15.0

    monkeypatch.setenv("CORAS_TEXTGEN_API_KEY", "k")
    set_settings(monkeypatch, {})
    monkeypatch.setenv("CORAS_TEXTGEN_TEMPERATURE", "1.5")
    assert resolve_config().temperature == 1.5


def test_bad_numeric_falls_back_to_default(monkeypatch):
    set_settings(
        monkeypatch,
        {"coras_textgen.apiKey": "k", "coras_textgen.temperature": "hot"},
    )
    assert resolve_config().temperature == 0.7


def test_empty_string_setting_falls_back(monkeypatch):
    monkeypatch.setenv("CORAS_TEXTGEN_API_KEY", "k")
    set_settings(monkeypatch, {"coras_textgen.model": "  "})
    assert resolve_config().model == "gpt-4o-mini"
