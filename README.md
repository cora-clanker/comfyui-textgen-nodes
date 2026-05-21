# comfyui-coras-textgen-nodes

**Cora's Textgen** — a ComfyUI custom-node pack with two nodes,
**Prompt Enhancer** and **Recaption**, that send your text (or an image)
plus a style-driven system prompt to an OpenAI-compatible
`/chat/completions` endpoint and output the reply with `<think>`
reasoning blocks stripped.

- Targets the **Nodes 2.0 (V3)** API.
- Endpoint and API key are set in the ComfyUI **Settings panel** (group:
  *Cora's Textgen*); system prompts come from per-node style dropdowns
  backed by user-editable YAML files.
- Works with any OpenAI-compatible server: OpenAI, Ollama, LM Studio,
  llama.cpp, vLLM, etc.

## Install

Clone (or copy) this folder into your ComfyUI `custom_nodes` directory and
restart ComfyUI:

```
ComfyUI/custom_nodes/comfyui-coras-textgen-nodes
```

`requests` is the only runtime dependency and is already bundled with ComfyUI;
`requirements.txt` lists it for standalone use.

## Configuration

Open **Settings → Cora's Textgen** and set:

| Setting | Default | Notes |
|---|---|---|
| API Base URL | `https://api.openai.com/v1` | The node calls `<base>/chat/completions`. |
| API Key | *(empty)* | Required. Stored locally, never in workflow files. |
| Temperature | `0.7` | |
| Request Timeout (s) | `60` | |
| Filter Vision-Capable Models (Recaption) | `true` | Substring heuristic on `/models` for the Recaption dropdown. Disable to see every model. |

> **The API key has no default.** A ComfyUI setting is only written to disk
> after you change it once, so you must enter the key in Settings (or provide
> `CORAS_TEXTGEN_API_KEY`) — otherwise the node fails with a clear message.

### Environment-variable alternative (headless / Docker)

Each setting has an env fallback, used when the setting is unset:
`CORAS_TEXTGEN_API_BASE`, `CORAS_TEXTGEN_API_KEY`,
`CORAS_TEXTGEN_TEMPERATURE`, `CORAS_TEXTGEN_TIMEOUT`,
`CORAS_TEXTGEN_RECAPTION_FILTER_VISION`.

**Precedence (highest first):** `comfy.settings.json` → environment
variable → built-in default. The `model` and `system_prompt` per chat
call come from on-node selections (model dropdown + style YAML) and are
not configured in Settings.

The model dropdowns talk to `/coras_textgen/models` (and
`/coras_textgen/models/vision` for Recaption), which proxy
`<api_base>/models`.

## The nodes

### Prompt Enhancer

**Inputs**

- `text` (required, multiline) — the draft prompt to be rewritten.
- `style` (dropdown) — populated from YAML files in
  `<user>/default/coras_textgen/prompts/prompt_enhancer/`. Each file has
  `name` (the display label) and `system_prompt` (the instruction sent
  to the model). On first launch the extension seeds
  `stable_diffusion.yml` (tag-style rewriter) and `flux.yml`
  (natural-language rewriter); existing files are never clobbered, so
  edits and additions survive restarts.
- `model` (dropdown) — populated by calling `<api_base>/models` on the
  configured endpoint.

**Output**

- `text` — the assistant reply with reasoning removed.

### Recaption

**Inputs**

- `image` (required) — only the first frame of a batched image is captioned.
- `style` (dropdown) — populated from YAML files in
  `<user>/default/coras_textgen/prompts/recaption/`. Each file has `name`
  (the display label) and `system_prompt` (sent to the model). On first
  launch the extension seeds `stable_diffusion.yml` and `flux.yml` with
  tag-style and natural-language captioners respectively; existing files
  are never clobbered, so edits and additions survive restarts.
- `model` (dropdown) — populated from `<api_base>/models`, then filtered
  by a name heuristic (`vision`, `vl`, `llava`, `gpt-4o`, `gemma`,
  `pixtral`, `molmo`, `claude`, `minicpm`, `florence`, `moondream`,
  `multimodal`). If the heuristic filters out every model the endpoint
  advertised, the unfiltered list is shown instead so the dropdown is
  never empty; toggle **Filter Vision-Capable Models** off in Settings
  to skip the heuristic entirely.

**Output**

- `text` — the assistant reply with reasoning removed.

The image is encoded as a base64 PNG and sent as an OpenAI-compatible
vision message (`image_url` content part). Works against any endpoint that
implements the vision content array — OpenAI, LM Studio (with a VL model),
LocalAI, vLLM, etc.

### `<think>` stripping

The output has reasoning content removed, handling the common variants:

- Balanced `<think>…</think>` blocks (any number, case-insensitive).
- A dangling `</think>` with no opening tag (some servers emit reasoning, then
  `</think>`, then the answer) — only the text after the last `</think>` is kept.
- An unclosed `<think>` (truncated reasoning) — everything from `<think>`
  onward is dropped.

Text with no think tags passes through unchanged (whitespace-trimmed).

## Caveats

- The backend reads ComfyUI's persisted settings file
  (`user/default/comfy.settings.json`) directly — there is no Python settings
  API. Reads are defensive (missing/empty/bad file → env → defaults).
- Multi-user ComfyUI stores settings under `user/<name>/…`; only the `default`
  user (plus env vars) is supported initially.
- V3 only — requires a ComfyUI build that ships `comfy_api.latest`.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install requests pytest pyyaml
pytest -q
```

Tests cover `strip_think` (all tag variants), `resolve_config` precedence,
the vision-model name heuristic, and the YAML-backed prompt-style loader;
none require a running ComfyUI.

## Publishing

Before publishing to the ComfyUI Registry, set `PublisherId` and the repository
URL in `pyproject.toml` (currently `CHANGEME`).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
