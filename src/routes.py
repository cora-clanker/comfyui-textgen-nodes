"""HTTP route registration for the Prompt Enhancer and Recaption dropdowns.

This module performs side effects on import: it registers
``GET /coras_textgen/models``, ``GET /coras_textgen/models/vision`` and
``GET /coras_textgen/prompt_styles/recaption`` on ComfyUI's ``PromptServer``.
The frontend reaches them under ``/api/...`` via ``Combo.Input``'s
``RemoteOptions``.

Importing this module outside ComfyUI (``server`` not on ``sys.path``) is a
no-op: the import fails, the caller catches it.
"""

import asyncio
import logging

from aiohttp import web
from server import PromptServer  # noqa: F401  -- only importable inside ComfyUI

from . import prompts
from .client import list_models, list_vision_models
from .config import resolve_config, resolve_recaption_filter

_logger = logging.getLogger(__name__)


@PromptServer.instance.routes.get("/coras_textgen/models")
async def coras_textgen_list_models(_request):
    """Return the endpoint's model ids as a JSON array.

    Defensive on purpose: any failure (no API key, endpoint down, no
    ``/models`` route on the server, malformed response) collapses to an
    empty array so the dropdown stays empty instead of breaking the UI.
    """
    try:
        cfg = resolve_config()
    except ValueError:
        return web.json_response([])

    try:
        models = await asyncio.to_thread(list_models, cfg)
    except Exception as exc:  # noqa: BLE001 -- any failure -> empty dropdown
        _logger.warning("coras_textgen: failed to list models: %s", exc)
        return web.json_response([])

    return web.json_response(models)


@PromptServer.instance.routes.get("/coras_textgen/models/vision")
async def coras_textgen_list_vision_models(_request):
    """Return vision-capable model ids (heuristic, toggleable via setting)."""
    try:
        cfg = resolve_config()
    except ValueError:
        return web.json_response([])

    filter_vision = resolve_recaption_filter()
    try:
        models = await asyncio.to_thread(
            list_vision_models, cfg, filter_vision=filter_vision,
        )
    except Exception as exc:  # noqa: BLE001 -- any failure -> empty dropdown
        _logger.warning("coras_textgen: failed to list vision models: %s", exc)
        return web.json_response([])

    return web.json_response(models)


@PromptServer.instance.routes.get("/coras_textgen/prompt_styles/recaption")
async def coras_textgen_list_recaption_styles(_request):
    """Return the available Recaption prompt-style display names."""
    try:
        styles = prompts.list_styles()
    except Exception as exc:  # noqa: BLE001 -- any failure -> empty dropdown
        _logger.warning("coras_textgen: failed to list prompt styles: %s", exc)
        return web.json_response([])

    return web.json_response([s["name"] for s in styles])
