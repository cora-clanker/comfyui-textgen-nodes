"""Minimal synchronous client for an OpenAI-compatible chat endpoint.

Kept synchronous so the same implementation serves both the async V3 node
(via ``asyncio.to_thread``) and the sync legacy node, with no event-loop
reentrancy concerns.
"""

import base64
import io as _io

import requests

from .config import TextGenConfig


# Substring keywords (case-insensitive) used to detect vision-capable models
# advertised by an OpenAI-compatible /models endpoint. The list errs on the
# side of catching known families; users can disable filtering entirely via
# the recaptionFilterVision setting if their endpoint exposes a name we miss.
_VISION_KEYWORDS = (
    "vision",
    "vl",
    "llava",
    "gpt-4o",
    "gemma-3",
    "qwen-vl",
    "internvl",
    "minicpm-v",
    "pixtral",
    "molmo",
    "claude",
    "kimi-vl",
)


def _is_vision_model(model_id: str) -> bool:
    """True if ``model_id`` looks vision-capable by name heuristic."""
    if not isinstance(model_id, str):
        return False
    lower = model_id.lower()
    return any(keyword in lower for keyword in _VISION_KEYWORDS)


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


def chat_completion_with_image(
    cfg: TextGenConfig,
    user_text: str,
    image_b64: str,
    *,
    mime: str = "image/png",
) -> str:
    """POST a vision chat completion (text + image) and return the reply.

    The user-message content is an array: when ``user_text`` is non-empty a
    text part is prepended, otherwise the image is sent alone (some
    OpenAI-compatible servers reject an empty text part). Same error
    semantics as :func:`chat_completion`.
    """
    url = f"{cfg.api_base}/chat/completions"
    user_content = [
        {
            "type": "image_url",
            "image_url": {"url": f"data:{mime};base64,{image_b64}"},
        }
    ]
    if user_text:
        user_content.insert(0, {"type": "text", "text": user_text})

    payload = {
        "model": cfg.model,
        "messages": [
            {"role": "system", "content": cfg.system_prompt},
            {"role": "user", "content": user_content},
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
        raise RuntimeError(f"{url} returned HTTP {resp.status_code}: {body}")

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


def list_models(cfg: TextGenConfig) -> list[str]:
    """GET ``<api_base>/models`` and return sorted, deduped model ids.

    OpenAI-compatible servers respond with ``{"data": [{"id": "..."}, ...]}``;
    we are forgiving about missing/malformed entries and just skip them.
    Raises ``RuntimeError`` on transport errors or non-2xx responses so the
    caller can decide how to surface the failure.
    """
    url = f"{cfg.api_base}/models"
    headers = {"Authorization": f"Bearer {cfg.api_key}"}

    try:
        resp = requests.get(url, headers=headers, timeout=cfg.timeout)
    except requests.RequestException as exc:
        raise RuntimeError(f"Request to {url} failed: {exc}") from exc

    if not resp.ok:
        body = resp.text[:500]
        raise RuntimeError(f"{url} returned HTTP {resp.status_code}: {body}")

    try:
        data = resp.json()
    except ValueError as exc:
        raise RuntimeError(f"Unexpected response from {url}: {resp.text[:500]}") from exc

    entries = data.get("data") if isinstance(data, dict) else None
    if not isinstance(entries, list):
        return []

    ids = {
        entry["id"]
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("id"), str) and entry["id"]
    }
    return sorted(ids)


def list_vision_models(cfg: TextGenConfig, *, filter_vision: bool = True) -> list[str]:
    """Wrap :func:`list_models` with an optional vision-keyword filter.

    With ``filter_vision=False`` the result is identical to ``list_models``
    so users can opt out when the endpoint advertises vision models under
    names the heuristic doesn't catch.
    """
    models = list_models(cfg)
    if not filter_vision:
        return models
    return [m for m in models if _is_vision_model(m)]


def tensor_to_png_b64(image) -> str:
    """Encode the first frame of a ComfyUI IMAGE tensor as a base64 PNG.

    ``image`` is shaped ``(B, H, W, C)`` with float values in [0, 1], either
    a ``torch.Tensor`` (the ComfyUI runtime case) or any array-like (tests).
    Only ``image[0]`` is encoded; callers handle batches by picking a frame.
    Raises ``ValueError`` for an empty batch.
    """
    import numpy as np
    from PIL import Image

    if hasattr(image, "cpu"):
        image = image.cpu().numpy()
    arr = np.asarray(image)
    if arr.ndim == 4:
        if arr.shape[0] == 0:
            raise ValueError("Recaption received an empty image batch")
        frame = arr[0]
    elif arr.ndim == 3:
        frame = arr
    else:
        raise ValueError(
            f"Recaption expected an image of shape (B,H,W,C) or (H,W,C), got {arr.shape}"
        )

    frame = (np.clip(frame, 0.0, 1.0) * 255.0).astype(np.uint8)
    pil = Image.fromarray(frame)
    buf = _io.BytesIO()
    pil.save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode("ascii")
