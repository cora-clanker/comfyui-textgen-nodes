import pytest

from src import config
from src.config import resolve_config, resolve_recaption_filter

_ENV_VARS = [
    "CORAS_TEXTGEN_API_BASE",
    "CORAS_TEXTGEN_API_KEY",
    "CORAS_TEXTGEN_TEMPERATURE",
    "CORAS_TEXTGEN_TIMEOUT",
    "CORAS_TEXTGEN_RECAPTION_FILTER_VISION",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch):
    """Isolate each test: no env vars and an empty settings file by default."""
    for var in _ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setattr(config, "_load_settings", lambda: {})


def set_settings(monkeypatch, data):
    monkeypatch.setattr(config, "_load_settings", lambda: data)


def _resolve(**overrides):
    """resolve_config requires model + system_prompt; tests usually don't care
    what they are, so default them here."""
    kwargs = {"system_prompt": "sp", "model": "m"}
    kwargs.update(overrides)
    return resolve_config(**kwargs)


def test_missing_api_key_raises(monkeypatch):
    with pytest.raises(ValueError, match="No API key"):
        _resolve()


def test_defaults_with_key_from_env(monkeypatch):
    monkeypatch.setenv("CORAS_TEXTGEN_API_KEY", "k")
    cfg = _resolve()
    assert cfg.api_base == "https://api.openai.com/v1"
    assert cfg.temperature == 0.7
    assert cfg.timeout == 60.0


def test_system_prompt_and_model_pass_through(monkeypatch):
    monkeypatch.setenv("CORAS_TEXTGEN_API_KEY", "k")
    cfg = _resolve(system_prompt="my system", model="my-model")
    assert cfg.system_prompt == "my system"
    assert cfg.model == "my-model"


def test_no_arg_call_works_for_route_handlers(monkeypatch):
    # Route handlers (e.g. /coras_textgen/models, .../models/vision) hit
    # resolve_config() with no chat-only fields. The signature MUST tolerate
    # that -- if it doesn't, the frontend Combo sits on "Loading..." forever
    # because the handler 500s.
    monkeypatch.setenv("CORAS_TEXTGEN_API_KEY", "k")
    cfg = resolve_config()
    assert cfg.api_key == "k"
    assert cfg.system_prompt == ""
    assert cfg.model == ""


def test_settings_override_env_for_api_key(monkeypatch):
    monkeypatch.setenv("CORAS_TEXTGEN_API_KEY", "env-key")
    set_settings(monkeypatch, {"coras_textgen.apiKey": "settings-key"})
    assert _resolve().api_key == "settings-key"


def test_api_base_trailing_slash_stripped(monkeypatch):
    set_settings(
        monkeypatch,
        {"coras_textgen.apiKey": "k", "coras_textgen.apiBase": "https://host/v1/"},
    )
    assert _resolve().api_base == "https://host/v1"


def test_numeric_from_settings_and_env(monkeypatch):
    set_settings(
        monkeypatch,
        {
            "coras_textgen.apiKey": "k",
            "coras_textgen.temperature": 0.2,
            "coras_textgen.timeout": 15,
        },
    )
    cfg = _resolve()
    assert cfg.temperature == 0.2
    assert cfg.timeout == 15.0

    monkeypatch.setenv("CORAS_TEXTGEN_API_KEY", "k")
    set_settings(monkeypatch, {})
    monkeypatch.setenv("CORAS_TEXTGEN_TEMPERATURE", "1.5")
    assert _resolve().temperature == 1.5


def test_bad_numeric_falls_back_to_default(monkeypatch):
    set_settings(
        monkeypatch,
        {"coras_textgen.apiKey": "k", "coras_textgen.temperature": "hot"},
    )
    assert _resolve().temperature == 0.7


def test_recaption_filter_default_true(monkeypatch):
    assert resolve_recaption_filter() is True


def test_recaption_filter_env_disables(monkeypatch):
    monkeypatch.setenv("CORAS_TEXTGEN_RECAPTION_FILTER_VISION", "false")
    assert resolve_recaption_filter() is False
    monkeypatch.setenv("CORAS_TEXTGEN_RECAPTION_FILTER_VISION", "0")
    assert resolve_recaption_filter() is False
    monkeypatch.setenv("CORAS_TEXTGEN_RECAPTION_FILTER_VISION", "No")
    assert resolve_recaption_filter() is False


def test_recaption_filter_settings_override_env(monkeypatch):
    monkeypatch.setenv("CORAS_TEXTGEN_RECAPTION_FILTER_VISION", "false")
    set_settings(monkeypatch, {"coras_textgen.recaptionFilterVision": True})
    assert resolve_recaption_filter() is True


def test_recaption_filter_settings_string_true(monkeypatch):
    set_settings(monkeypatch, {"coras_textgen.recaptionFilterVision": "yes"})
    assert resolve_recaption_filter() is True


def test_recaption_filter_garbage_falls_back(monkeypatch):
    monkeypatch.setenv("CORAS_TEXTGEN_RECAPTION_FILTER_VISION", "maybe")
    assert resolve_recaption_filter() is True
