"""comfyui-textgen-nodes package entrypoint.

ComfyUI discovers a node pack by either a ``comfy_entrypoint`` (V3) or
``NODE_CLASS_MAPPINGS`` (legacy). We expose exactly one of them depending on
whether the running ComfyUI ships ``comfy_api``, so the node is never
registered twice.
"""

WEB_DIRECTORY = "./web/js"

try:
    import comfy_api.latest  # noqa: F401  -- probe for V3 availability

    _HAS_V3 = True
except Exception:
    _HAS_V3 = False

if _HAS_V3:
    try:
        from .src.nodes_v3 import comfy_entrypoint  # noqa: F401
    except ImportError:  # imported outside the ComfyUI package (e.g. tests)
        from src.nodes_v3 import comfy_entrypoint  # noqa: F401

    NODE_CLASS_MAPPINGS = {}
    NODE_DISPLAY_NAME_MAPPINGS = {}
else:
    try:
        from .src.nodes_legacy import (  # noqa: F401
            NODE_CLASS_MAPPINGS,
            NODE_DISPLAY_NAME_MAPPINGS,
        )
    except ImportError:  # imported outside the ComfyUI package (e.g. tests)
        from src.nodes_legacy import (  # noqa: F401
            NODE_CLASS_MAPPINGS,
            NODE_DISPLAY_NAME_MAPPINGS,
        )

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
    "comfy_entrypoint",
]
