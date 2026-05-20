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

_PROMPT_ENHANCER_DESCRIPTION = (
    "Run a prompt through the configured chat endpoint and return the reply "
    "with <think> reasoning blocks removed. The model dropdown is populated "
    "from <api_base>/models; use the refresh button to re-fetch. System "
    "prompt, endpoint and API key come from Settings -> TextGen."
)


class TextGenAdvancedNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="TextGenOpenAI",
            display_name="Text Gen Advanced",
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


class PromptEnhancerNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="TextGenPromptEnhancer",
            display_name="Prompt Enhancer",
            category="text/llm",
            description=_PROMPT_ENHANCER_DESCRIPTION,
            inputs=[
                io.String.Input(
                    "text",
                    multiline=True,
                    default="",
                    tooltip="User message sent to the model.",
                ),
                io.Combo.Input(
                    "model",
                    options=[],
                    remote=io.RemoteOptions(
                        route="/textgen/models",
                        refresh_button=True,
                    ),
                    tooltip="Models advertised by the configured endpoint.",
                ),
            ],
            outputs=[io.String.Output(display_name="text")],
        )

    @classmethod
    async def execute(cls, text, model) -> io.NodeOutput:
        cfg = resolve_config(model_override=model)
        raw = await asyncio.to_thread(chat_completion, cfg, text)
        return io.NodeOutput(strip_think(raw))


class TextGenExtension(ComfyExtension):
    async def get_node_list(self):
        return [TextGenAdvancedNode, PromptEnhancerNode]


async def comfy_entrypoint() -> ComfyExtension:
    return TextGenExtension()
