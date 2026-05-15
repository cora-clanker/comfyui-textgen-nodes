"""Legacy (pre-V3) node definition.

Used as a fallback on ComfyUI builds that do not ship ``comfy_api``. Shares the
config/client/think logic with the V3 node so behaviour is identical.
"""

from .client import chat_completion
from .config import resolve_config
from .think import strip_think


class TextGenNodeLegacy:
    CATEGORY = "text/llm"
    FUNCTION = "run"
    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("text",)
    DESCRIPTION = (
        "Send text and a system prompt to an OpenAI-compatible chat endpoint "
        "and return the reply with <think> reasoning blocks removed."
    )

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"multiline": True, "default": ""}),
            },
            "optional": {
                "system_prompt": ("STRING", {"multiline": True, "default": ""}),
                "model": ("STRING", {"default": ""}),
            },
        }

    def run(self, text, system_prompt="", model=""):
        cfg = resolve_config(system_prompt_override=system_prompt, model_override=model)
        raw = chat_completion(cfg, text)
        return (strip_think(raw),)


NODE_CLASS_MAPPINGS = {"TextGenOpenAI": TextGenNodeLegacy}
NODE_DISPLAY_NAME_MAPPINGS = {"TextGenOpenAI": "Text Gen (OpenAI-compatible)"}
