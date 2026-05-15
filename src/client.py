"""Minimal synchronous client for an OpenAI-compatible chat endpoint.

Kept synchronous so the same implementation serves both the async V3 node
(via ``asyncio.to_thread``) and the sync legacy node, with no event-loop
reentrancy concerns.
"""

import requests

from .config import TextGenConfig


def chat_completion(cfg: TextGenConfig, user_text: str) -> str:
    """POST a chat completion and return the assistant message content.

    Raises ``RuntimeError`` on transport errors, non-2xx responses, or an
    unexpected response shape.
    """
    url = f"{cfg.api_base}/chat/completions"
    payload = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": cfg.system_prompt},
            {"role": "user", "content": user_text},
        ],
        "temperature": cfg.temperature,
    }
    headers = {
        "Authorization": f"Bearer {cfg.api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=cfg.timeout)
    except requests.RequestException as exc:
        raise RuntimeError(f"Request to {url} failed: {exc}") from exc

    if not resp.ok:
        body = resp.text[:500]
        raise RuntimeError(
            f"{url} returned HTTP {resp.status_code}: {body}"
        )

    try:
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
    except (ValueError, KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(
            f"Unexpected response from {url}: {resp.text[:500]}"
        ) from exc

    if content is None or content == "":
        raise RuntimeError(f"{url} returned an empty completion.")

    return content
