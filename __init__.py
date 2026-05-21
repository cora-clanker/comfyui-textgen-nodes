"""comfyui-coras-textgen-nodes package entrypoint.

V3 (Nodes 2.0) only. ComfyUI discovers the pack by calling
``comfy_entrypoint``; ``NODE_CLASS_MAPPINGS`` is ``None`` because the V3
loader checks it first and would deadlock on an empty dict.

The probe at the top lets pytest collect the package outside ComfyUI
without exploding on the ``comfy_api`` import; in that environment
``comfy_entrypoint`` is just ``None``.
"""

WEB_DIRECTORY = "./web/js"

try:
    import comfy_api.latest  # noqa: F401  -- probe; only register inside ComfyUI
    _IN_COMFYUI = True
except Exception:
    _IN_COMFYUI = False

if _IN_COMFYUI:
    try:
        from .src.nodes_v3 import comfy_entrypoint  # noqa: F401
    except ImportError:  # imported outside the parent package (rare; tooling)
        from src.nodes_v3 import comfy_entrypoint  # noqa: F401

    # Side-effect import: registers /coras_textgen/* routes on PromptServer.
    # Best effort -- if ``server`` isn't on sys.path (tooling that probes the
    # entrypoint outside ComfyUI), skip silently; the dropdowns just won't
    # work in that environment.
    try:
        from .src import routes  # noqa: F401
    except ImportError:
        try:
            from src import routes  # noqa: F401
        except ImportError:
            pass
else:
    comfy_entrypoint = None

# Must be None, not {}. ComfyUI's loader gate is
# ``hasattr(...) and getattr(...) is not None`` and it ``return``s on the
# V1 branch BEFORE reaching the comfy_entrypoint (V3) branch. An empty
# dict is "not None", so {} traps the loader in the V1 path, registers
# zero nodes, and never calls comfy_entrypoint. None skips it correctly.
NODE_CLASS_MAPPINGS = None
NODE_DISPLAY_NAME_MAPPINGS = None

__all__ = [
    "NODE_CLASS_MAPPINGS",
    "NODE_DISPLAY_NAME_MAPPINGS",
    "WEB_DIRECTORY",
    "comfy_entrypoint",
]
