# comfyui-textgen-nodes

A ComfyUI custom-node pack with a single node, **Text Gen (OpenAI-compatible)**,
that sends your text plus a system prompt to an OpenAI-compatible
`/chat/completions` endpoint and outputs the reply with `<think>` reasoning
blocks stripped.

- Targets the **Nodes 2.0 (V3)** API, with an automatic **legacy fallback** for
  older ComfyUI builds that don't ship `comfy_api`.
- Endpoint, API key, model, and default system prompt are set in the ComfyUI
  **Settings panel** (group: *TextGen*).
- Works with any OpenAI-compatible server: OpenAI, Ollama, LM Studio,
  llama.cpp, vLLM, etc.

## Install

Clone (or copy) this folder into your ComfyUI `custom_nodes` directory and
restart ComfyUI:

```
ComfyUI/custom_nodes/comfyui-textgen-nodes
```

`requests` is the only runtime dependency and is already bundled with ComfyUI;
`requirements.txt` lists it for standalone use.

## Configuration

Open **Settings → TextGen** and set:

| Setting | Default | Notes |
|---|---|---|
| API Base URL | `https://api.openai.com/v1` | The node calls `<base>/chat/completions`. |
| API Key | *(empty)* | Required. Stored locally, never in workflow files. |
| Model | `gpt-4o-mini` | Overridable per-node. |
| System Prompt | `You are a helpful assistant.` | Overridable per-node (single-line in Settings). |
| Temperature | `0.7` | |
| Request Timeout (s) | `60` | |

> **The API key has no default.** A ComfyUI setting is only written to disk
> after you change it once, so you must enter the key in Settings (or provide
> `TEXTGEN_API_KEY`) — otherwise the node fails with a clear message.

### Environment-variable alternative (headless / Docker)

Each setting has an env fallback, used when the setting is unset:
`TEXTGEN_API_BASE`, `TEXTGEN_API_KEY`, `TEXTGEN_MODEL`,
`TEXTGEN_SYSTEM_PROMPT`, `TEXTGEN_TEMPERATURE`, `TEXTGEN_TIMEOUT`.

**Precedence (highest first):** per-node input override (model / system prompt
only) → `comfy.settings.json` → environment variable → built-in default.

## The node

**Inputs**

- `text` (required, multiline) — the user message.
- `system_prompt` (optional, multiline) — override; blank uses the Settings value.
- `model` (optional) — override; blank uses the Settings value.

**Output**

- `text` — the assistant reply with reasoning removed.

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
