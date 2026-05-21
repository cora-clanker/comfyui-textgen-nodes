"""V3 (Nodes 2.0) node definitions for Cora's Textgen."""

import asyncio

from comfy_api.latest import ComfyExtension, io

from . import prompts
from .client import (
    chat_completion,
    chat_completion_with_image,
    tensor_to_png_b64,
)
from .config import resolve_config
from .think import strip_think

_PROMPT_ENHANCER_DESCRIPTION = (
    "Rewrite a draft prompt through the configured chat endpoint and return "
    "the reply with <think> reasoning blocks removed. The system prompt comes "
    "from the selected style (YAML files under "
    "<user>/default/coras_textgen/prompts/prompt_enhancer/). The model "
    "dropdown is populated from <api_base>/models. Endpoint and API key come "
    "from Settings -> Cora's Textgen."
)

_RECAPTION_DESCRIPTION = (
    "Caption an image by sending it to an OpenAI-compatible vision chat "
    "endpoint. The system prompt is selected from YAML files in "
    "<user>/default/coras_textgen/prompts/recaption/. The model dropdown is "
    "filtered to vision-capable ids by a name heuristic; disable the filter "
    "in Settings -> Cora's Textgen -> Recaption to show every model."
)

_REFINE_TEXT_DESCRIPTION = (
    "Sit between an upstream text node and downstream consumers to capture "
    "the upstream text into an editable multiline field. With lock off the "
    "node passes the upstream input through and repopulates the widget after "
    "each run. The lock flips on automatically the moment you type in the "
    "widget; while locked, the widget value is output and the upstream input "
    "is ignored. Untick lock to resync from upstream."
)


class CorasPromptEnhancerNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="CorasPromptEnhancer",
            display_name="Prompt Enhancer",
            category="textgen",
            description=_PROMPT_ENHANCER_DESCRIPTION,
            inputs=[
                io.String.Input(
                    "text",
                    multiline=True,
                    default="",
                    tooltip="Draft prompt the model should rewrite.",
                ),
                io.Combo.Input(
                    "style",
                    options=[],
                    remote=io.RemoteOptions(
                        route="/coras_textgen/prompt_styles/prompt_enhancer",
                        refresh_button=False,
                    ),
                    tooltip=(
                        "Prompt style. Edit or add YAML files under "
                        "<user>/default/coras_textgen/prompts/prompt_enhancer/. "
                        "Replaces the Settings system prompt for this node."
                    ),
                ),
                io.Combo.Input(
                    "model",
                    options=[],
                    remote=io.RemoteOptions(
                        route="/coras_textgen/models",
                        refresh_button=False,
                    ),
                    tooltip="Models advertised by the configured endpoint.",
                ),
            ],
            outputs=[io.String.Output(display_name="text")],
        )

    @classmethod
    def validate_inputs(cls, **kwargs):
        # The model and style Combos are remote-populated (options=[] in the
        # schema), so ComfyUI's built-in "value in list" check would reject
        # any value at submit time. Defining this method with **kwargs tells
        # the executor to skip its static per-input checks and defer to us;
        # any non-empty value is accepted and resolved at run time.
        return True

    @classmethod
    async def execute(cls, text, style, model) -> io.NodeOutput:
        system_prompt = prompts.get_system_prompt("prompt_enhancer", style)
        if system_prompt is None:
            raise RuntimeError(
                f"Prompt Enhancer: prompt style {style!r} not found"
            )
        cfg = resolve_config(system_prompt=system_prompt, model=model)
        raw = await asyncio.to_thread(chat_completion, cfg, text)
        return io.NodeOutput(strip_think(raw))


class CorasRecaptionNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="CorasRecaption",
            display_name="Recaption",
            category="textgen",
            description=_RECAPTION_DESCRIPTION,
            inputs=[
                io.Image.Input("image"),
                io.Combo.Input(
                    "style",
                    options=[],
                    remote=io.RemoteOptions(
                        route="/coras_textgen/prompt_styles/recaption",
                        refresh_button=False,
                    ),
                    tooltip=(
                        "Prompt style. Edit or add YAML files under "
                        "<user>/default/coras_textgen/prompts/recaption/."
                    ),
                ),
                io.Combo.Input(
                    "model",
                    options=[],
                    remote=io.RemoteOptions(
                        route="/coras_textgen/models/vision",
                        refresh_button=False,
                    ),
                    tooltip="Vision-capable models advertised by the configured endpoint.",
                ),
            ],
            outputs=[io.String.Output(display_name="text")],
        )

    @classmethod
    def validate_inputs(cls, **kwargs):
        # Both `style` and `model` are remote-populated Combos with empty
        # static options. Same trick as CorasPromptEnhancerNode: declaring
        # validate_inputs with **kwargs tells the executor to skip its
        # per-input static checks and defer to us; we accept anything.
        return True

    @classmethod
    async def execute(cls, image, style, model) -> io.NodeOutput:
        system_prompt = prompts.get_system_prompt("recaption", style)
        if system_prompt is None:
            raise RuntimeError(f"Recaption: prompt style {style!r} not found")
        cfg = resolve_config(system_prompt=system_prompt, model=model)
        image_b64 = await asyncio.to_thread(tensor_to_png_b64, image)
        raw = await asyncio.to_thread(chat_completion_with_image, cfg, "", image_b64)
        return io.NodeOutput(strip_think(raw))


class CorasRefineTextNode(io.ComfyNode):
    @classmethod
    def define_schema(cls) -> io.Schema:
        return io.Schema(
            node_id="CorasRefineText",
            display_name="Refine Text",
            category="text",
            description=_REFINE_TEXT_DESCRIPTION,
            inputs=[
                io.String.Input(
                    "text",
                    multiline=True,
                    default="",
                    force_input=True,
                    optional=True,
                    tooltip="Upstream text. Socket-only; wire from Prompt Enhancer or any string source.",
                ),
                io.Boolean.Input(
                    "lock",
                    default=False,
                    tooltip=(
                        "When on, output the edited text below instead of the "
                        "upstream input. Auto-engages when you type in the widget."
                    ),
                ),
                io.String.Input(
                    "edited_text",
                    multiline=True,
                    default="",
                    tooltip=(
                        "Editable copy of the upstream text. Auto-populated "
                        "after each run while unlocked; freely edited while locked."
                    ),
                ),
            ],
            outputs=[io.String.Output(display_name="text")],
        )

    @classmethod
    async def execute(cls, lock: bool, edited_text: str, text: str = "") -> io.NodeOutput:
        # Always emit the upstream text to the frontend so the JS extension
        # can detect "upstream drifted while locked" and surface a warning.
        out = edited_text if lock else text
        return io.NodeOutput(out, ui={"upstream_text": (text,)})


class CorasTextGenExtension(ComfyExtension):
    async def on_load(self):
        prompts.seed_defaults()

    async def get_node_list(self):
        return [CorasPromptEnhancerNode, CorasRecaptionNode, CorasRefineTextNode]


async def comfy_entrypoint() -> ComfyExtension:
    return CorasTextGenExtension()
