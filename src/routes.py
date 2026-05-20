"""HTTP route registration for the Prompt Enhancer model dropdown.

This module performs side effects on import: it registers
``GET /coras_textgen/models`` on ComfyUI's ``PromptServer``. The frontend
reaches it as ``/api/coras_textgen/models`` and the ``Combo.Input``'s
``RemoteOptions`` points there.

Importing this module outside ComfyUI (``server`` not on ``sys.path``) is a
no-op: the import fails, the caller catches it.
"""

import asyncio
import logging

from aiohttp import web
from server import PromptServer  # noqa: F401  -- only importable inside ComfyUI

from .client import list_models
from .config import resolve_config

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
