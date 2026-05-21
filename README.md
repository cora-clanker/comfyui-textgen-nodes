# comfyui-coras-textgen-nodes

**Cora's Textgen** — a ComfyUI custom-node pack with three nodes,
**Prompt Enhancer**, **Textgen Advanced**, and **Recaption**, that send your
text (or an image) plus a system prompt to an OpenAI-compatible
`/chat/completions` endpoint and output the reply with `<think>` reasoning
blocks stripped.

- Targets the **Nodes 2.0 (V3)** API, with an automatic **legacy fallback** for
  older ComfyUI builds that don't ship `comfy_api`.
- Endpoint, API key, model, and default system prompt are set in the ComfyUI
  **Settings panel** (group: *Cora's Textgen*).
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
| Model | `gpt-4o-mini` | Overridable per-node. |
| System Prompt | `You are a helpful assistant.` | Overridable per-node (single-line in Settings). |
| Temperature | `0.7` | |
| Request Timeout (s) | `60` | |
| Filter Vision-Capable Models (Recaption) | `true` | Substring heuristic on `/models` for the Recaption dropdown. Disable to see every model. |

> **The API key has no default.** A ComfyUI setting is only written to disk
> after you change it once, so you must enter the key in Settings (or provide
> `CORAS_TEXTGEN_API_KEY`) — otherwise the node fails with a clear message.

### Environment-variable alternative (headless / Docker)

Each setting has an env fallback, used when the setting is unset:
`CORAS_TEXTGEN_API_BASE`, `CORAS_TEXTGEN_API_KEY`, `CORAS_TEXTGEN_MODEL`,
`CORAS_TEXTGEN_SYSTEM_PROMPT`, `CORAS_TEXTGEN_TEMPERATURE`,
`CORAS_TEXTGEN_TIMEOUT`, `CORAS_TEXTGEN_RECAPTION_FILTER_VISION`.

**Precedence (highest first):** per-node input override (model / system prompt
only) → `comfy.settings.json` → environment variable → built-in default.

The Prompt Enhancer dropdown talks to `/coras_textgen/models` (frontend path
`/api/coras_textgen/models`), which proxies `<api_base>/models` and uses the
same config-resolution chain.

## The nodes

### Prompt Enhancer (V3 only)

**Inputs**

- `text` (required, multiline) — the draft prompt to be rewritten.
- `style` (dropdown) — populated from YAML files in
  `<user>/default/coras_textgen/prompts/prompt_enhancer/`. Each file has
  `name` (the display label) and `system_prompt` (the instruction sent
  to the model). On first launch the extension seeds
  `stable_diffusion.yml` (tag-style rewriter) and `flux.yml`
  (natural-language rewriter); existing files are never clobbered, so
  edits and additions survive restarts. **The selected style fully
  replaces Settings → System Prompt for this node** — that setting now
  only affects **Textgen Advanced**.
- `model` (dropdown) — populated by calling `<api_base>/models` on the
  configured endpoint.

**Output**

- `text` — the assistant reply with reasoning removed.

The model dropdown is empty if the endpoint is unreachable, returns no
`/models` route, or no API key is configured — in any of those cases
**Cora's Textgen Advanced** remains usable because its `model` is free-text.

### Recaption (V3 only)

**Inputs**

- `image` (required) — only the first frame of a batched image is captioned.
- `style` (dropdown) — populated from YAML files in
  `<user>/default/coras_textgen/prompts/recaption/`. Each file has `name`
  (the display label) and `system_prompt` (sent to the model). On first
  launch the extension seeds `stable_diffusion.yml` and `flux.yml` with
  tag-style and natural-language captioners respectively; existing files
  are never clobbered, so edits and additions survive restarts.
- `model` (dropdown) — populated from `<api_base>/models`, then filtered
  by a name heuristic (`vision`, `vl`, `llava`, `gpt-4o`, `gemma-3`,
  `qwen-vl`, `internvl`, `minicpm-v`, `pixtral`, `molmo`, `claude`,
  `kimi-vl`). Toggle **Filter Vision-Capable Models** off in Settings to
  show every model the endpoint advertises.

**Output**

- `text` — the assistant reply with reasoning removed.

The image is encoded as a base64 PNG and sent as an OpenAI-compatible
vision message (`image_url` content part). Works against any endpoint that
implements the vision content array — OpenAI, LM Studio (with a VL model),
LocalAI, vLLM, etc.

### Cora's Textgen Advanced

**Inputs**

- `text` (required, multiline) — the user message.
- `system_prompt` (optional, multiline) — override; blank uses the Settings value.
- `model` (optional) — override; blank uses the Settings value.

**Output**

- `text` — the assistant reply with reasoning removed.

Available on both V3 ComfyUI and the legacy fallback build.

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
- The V3 `comfy_api` surface is still evolving; the legacy node covers older
  builds.

## Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install requests pytest
pytest -q
```

Tests cover `strip_think` (all tag variants) and `resolve_config` precedence;
neither requires a running ComfyUI.

## Publishing

Before publishing to the ComfyUI Registry, set `PublisherId` and the repository
URL in `pyproject.toml` (currently `CHANGEME`).

## License

GPL-3.0-or-later. See [LICENSE](LICENSE).
