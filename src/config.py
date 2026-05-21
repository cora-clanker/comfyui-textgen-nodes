"""Resolve runtime configuration for Cora's Textgen.

ComfyUI has no server-side settings API, so values set in the **Settings panel**
(registered by ``web/js/coras_textgen_settings.js``) are read back from the file
ComfyUI persists them to: ``<user_dir>/default/comfy.settings.json``, keyed by
the exact setting id. Reading that file directly is a community pattern, so this
module is deliberately defensive: a missing file, empty file, malformed JSON, or
missing key all fall through to environment variables and then built-in
defaults.

The ``system_prompt`` and ``model`` fields of :class:`TextGenConfig` are not in
the fallback chain -- both nodes pass them directly from their on-screen
inputs (style YAML + model dropdown). Settings/env only cover the cross-cutting
connection knobs (api_base, api_key, temperature, timeout).
"""

import json
import os
from dataclasses import dataclass

# Setting ids -- MUST stay in sync with web/js/coras_textgen_settings.js.
_SETTING_API_BASE = "coras_textgen.apiBase"
_SETTING_API_KEY = "coras_textgen.apiKey"
_SETTING_TEMPERATURE = "coras_textgen.temperature"
_SETTING_TIMEOUT = "coras_textgen.timeout"
_SETTING_RECAPTION_FILTER_VISION = "coras_textgen.recaptionFilterVision"

_DEFAULT_API_BASE = "https://api.openai.com/v1"
_DEFAULT_TEMPERATURE = 0.7
_DEFAULT_TIMEOUT = 60.0


@dataclass
class TextGenConfig:
    api_base: str
    api_key: str
    model: str
    system_prompt: str
    temperature: float
    timeout: float


def _settings_path():
    """Best-effort absolute path to ComfyUI's persisted settings file.

    Returns ``None`` when not running inside ComfyUI (e.g. unit tests).
    """
    try:
        import folder_paths  # provided by ComfyUI on sys.path

        base = folder_paths.get_user_directory()
    except Exception:
        return None
    return os.path.join(base, "default", "comfy.settings.json")


def _load_settings():
    """Load the settings file as a dict; never raises."""
    path = _settings_path()
    if not path:
        return {}
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _clean(value):
    """Normalise a candidate to a non-empty stripped string, or ``None``."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _pick_str(*candidates, default):
    for candidate in candidates:
        cleaned = _clean(candidate)
        if cleaned is not None:
            return cleaned
    return default


def _pick_float(*candidates, default):
    for candidate in candidates:
        cleaned = _clean(candidate)
        if cleaned is None:
            continue
        try:
            return float(cleaned)
        except ValueError:
            continue
    return default


_TRUE_VALUES = {"1", "true", "yes", "on"}
_FALSE_VALUES = {"0", "false", "no", "off"}


def _pick_bool(*candidates, default):
    """Pick the first non-empty candidate that parses as a boolean.

    Accepts native ``bool`` plus the string forms 1/0, true/false, yes/no,
    on/off (case-insensitive). Anything else is treated as "not specified"
    and the next candidate is tried; defaults to ``default``.
    """
    for candidate in candidates:
        if isinstance(candidate, bool):
            return candidate
        cleaned = _clean(candidate)
        if cleaned is None:
            continue
        lower = cleaned.lower()
        if lower in _TRUE_VALUES:
            return True
        if lower in _FALSE_VALUES:
            return False
    return default


def resolve_config(*, system_prompt: str = "", model: str = "") -> TextGenConfig:
    """Build a :class:`TextGenConfig` from settings/env plus the caller's
    ``system_prompt`` and ``model``.

    Both kwargs default to ``""`` so route handlers that only need the
    connection config (api_base/api_key/timeout) can call ``resolve_config()``
    without supplying chat-only fields. Nodes that actually issue a chat
    completion always pass real values for both.

    Raises ``ValueError`` if no API key can be found, since there is no safe
    default for it.
    """
    s = _load_settings()
    env = os.environ

    api_base = _pick_str(
        s.get(_SETTING_API_BASE),
        env.get("CORAS_TEXTGEN_API_BASE"),
        default=_DEFAULT_API_BASE,
    ).rstrip("/")

    api_key = _pick_str(
        s.get(_SETTING_API_KEY),
        env.get("CORAS_TEXTGEN_API_KEY"),
        default="",
    )
    if not api_key:
        raise ValueError(
            "No API key configured. Set it in ComfyUI Settings -> Cora's "
            "Textgen -> API Key, or via the CORAS_TEXTGEN_API_KEY environment "
            "variable."
        )

    temperature = _pick_float(
        s.get(_SETTING_TEMPERATURE),
        env.get("CORAS_TEXTGEN_TEMPERATURE"),
        default=_DEFAULT_TEMPERATURE,
    )

    timeout = _pick_float(
        s.get(_SETTING_TIMEOUT),
        env.get("CORAS_TEXTGEN_TIMEOUT"),
        default=_DEFAULT_TIMEOUT,
    )

    return TextGenConfig(
        api_base=api_base,
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        temperature=temperature,
        timeout=timeout,
    )


def resolve_recaption_filter() -> bool:
    """Read the Recaption vision-filter toggle (settings -> env -> default).

    Kept separate from :func:`resolve_config` because the flag belongs to the
    /models route, not to a chat completion. Default ``True``.
    """
    s = _load_settings()
    env = os.environ
    return _pick_bool(
        s.get(_SETTING_RECAPTION_FILTER_VISION),
        env.get("CORAS_TEXTGEN_RECAPTION_FILTER_VISION"),
        default=True,
    )
