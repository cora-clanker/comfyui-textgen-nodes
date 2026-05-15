import { app } from "../../scripts/app.js";

// Registers the TextGen settings group in ComfyUI's Settings panel.
//
// ComfyUI persists these values server-side to
// `user/default/comfy.settings.json`, keyed by the `id` strings below. The
// Python side (src/config.py) reads that file -- the ids MUST stay in sync.
//
// Note: a setting is only written to disk after the user changes it; the
// `defaultValue` here is a UI hint, not a persisted value. The API key in
// particular must be entered (or supplied via the TEXTGEN_API_KEY env var) or
// the node errors with a clear message.
app.registerExtension({
  name: "comfyui-textgen-nodes",
  settings: [
    {
      id: "textgen.apiBase",
      name: "API Base URL",
      category: ["TextGen", "Connection", "API Base URL"],
      type: "text",
      defaultValue: "https://api.openai.com/v1",
      tooltip:
        "Base URL of the OpenAI-compatible API (the node calls <base>/chat/completions).",
    },
    {
      id: "textgen.apiKey",
      name: "API Key",
      category: ["TextGen", "Connection", "API Key"],
      type: "text",
      defaultValue: "",
      tooltip:
        "Bearer token sent to the endpoint. Stored locally in comfy.settings.json, not in workflow files.",
      attrs: { type: "password" },
    },
    {
      id: "textgen.model",
      name: "Model",
      category: ["TextGen", "Generation", "Model"],
      type: "text",
      defaultValue: "gpt-4o-mini",
      tooltip: "Default model name. Can be overridden per-node.",
    },
    {
      id: "textgen.systemPrompt",
      name: "System Prompt",
      category: ["TextGen", "Generation", "System Prompt"],
      type: "text",
      defaultValue: "You are a helpful assistant.",
      tooltip:
        "Default system prompt. Settings input is single-line; use the node's multiline override for long prompts.",
    },
    {
      id: "textgen.temperature",
      name: "Temperature",
      category: ["TextGen", "Generation", "Temperature"],
      type: "number",
      defaultValue: 0.7,
      attrs: { min: 0, max: 2, step: 0.1 },
      tooltip: "Sampling temperature passed to the API.",
    },
    {
      id: "textgen.timeout",
      name: "Request Timeout (s)",
      category: ["TextGen", "Connection", "Request Timeout"],
      type: "number",
      defaultValue: 60,
      attrs: { min: 1, step: 1 },
      tooltip: "HTTP request timeout in seconds.",
    },
  ],
});
