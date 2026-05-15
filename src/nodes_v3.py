"""V3 (Nodes 2.0) node definition.

Imported only when ``comfy_api`` is available (guarded in the package
``__init__``), so the ``comfy_api`` import here is safe.
"""

import asyncio

from comfy_api.latest import ComfyExtension, io

from .client import chat_completion
from .config import resolve_config
from .think import strip_think

_DESCRIPTION = (
    "Send text and a system prompt to an OpenAI-compatible chat endpoint and "
    "return the reply with <think> reasoning blocks removed. Endpoint, API key, "
    "model and default system prompt are configured in Settings -> TextGen; the "
    "model and system prompt can be overridden per-node."
)


class TextGenNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="TextGenOpenAI",
            display_name="Text Gen (OpenAI-compatible)",
            category="text/llm",
            description=_DESCRIPTION,
            inputs=[
                io.String.Input(
                    "text",
                    multiline=True,
                    default="",
                    tooltip="User message sent to the model.",
                ),
                io.String.Input(
                    "system_prompt",
                    multiline=True,
                    default="",
                    optional=True,
                    tooltip="Override the system prompt. Blank = use Settings.",
                ),
                io.String.Input(
                    "model",
                    default="",
                    optional=True,
                    tooltip="Override the model name. Blank = use Settings.",
                ),
            ],
            outputs=[io.String.Output(display_name="text")],
        )

    @classmethod
    async def execute(cls, text, system_prompt="", model="") -> io.NodeOutput:
        cfg = resolve_config(system_prompt_override=system_prompt, model_override=model)
        raw = await asyncio.to_thread(chat_completion, cfg, text)
        return io.NodeOutput(strip_think(raw))


class TextGenExtension(ComfyExtension):
    async def get_node_list(self):
        return [TextGenNode]


async def comfy_entrypoint() -> ComfyExtension:
    return TextGenExtension()
