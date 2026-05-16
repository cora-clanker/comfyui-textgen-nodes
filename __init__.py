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

    # Must be None, not {}. ComfyUI's loader gate is
    # `hasattr(...) and getattr(...) is not None` and it `return`s on the
    # V1 branch BEFORE reaching the comfy_entrypoint (V3) branch. An empty
    # dict is "not None", so {} traps the loader in the V1 path, registers
    # zero nodes, and never calls comfy_entrypoint. None skips it correctly.
    NODE_CLASS_MAPPINGS = None
    NODE_DISPLAY_NAME_MAPPINGS = None
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
