"""Strip ``<think>`` reasoning blocks from model output.

Reasoning models emit their chain of thought wrapped in ``<think>...</think>``.
Different servers format this inconsistently, so :func:`strip_think` handles the
realistic variants rather than assuming well-formed tags.
"""

import re

# Tolerate surrounding whitespace inside the tag, e.g. ``< think >`` / ``</ think>``.
_OPEN = r"<\s*think\s*>"
_CLOSE = r"<\s*/\s*think\s*>"

_PAIRED = re.compile(_OPEN + r".*?" + _CLOSE, re.IGNORECASE | re.DOTALL)
_OPEN_RE = re.compile(_OPEN, re.IGNORECASE)
_CLOSE_RE = re.compile(_CLOSE, re.IGNORECASE)
_UNCLOSED = re.compile(_OPEN + r".*\Z", re.IGNORECASE | re.DOTALL)


def strip_think(text: str) -> str:
    """Return ``text`` with reasoning content removed.

    Handles, in order:

    1. Well-formed ``<think>...</think>`` blocks (any number, case-insensitive).
    2. A dangling ``</think>`` with no opening tag (some servers emit the
       reasoning, then ``</think>``, then the answer) -> keep only what follows
       the last ``</think>``.
    3. An unclosed ``<think>`` (reasoning truncated mid-stream) -> drop from the
       first ``<think>`` to the end.

    Surrounding whitespace left behind is trimmed. Input without any think tags
    is returned unchanged (apart from trimming).
    """
    if not text:
        return text

    # 1. Remove all balanced blocks.
    out = _PAIRED.sub("", text)

    # 2. Dangling close with no surviving open tag.
    if _CLOSE_RE.search(out) and not _OPEN_RE.search(out):
        out = out[_last_close_end(out):]

    # 3. Unclosed open tag.
    elif _OPEN_RE.search(out) and not _CLOSE_RE.search(out):
        out = _UNCLOSED.sub("", out)

    return out.strip()


def _last_close_end(text: str) -> int:
    """Index just past the final ``</think>`` in ``text``."""
    end = 0
    for m in _CLOSE_RE.finditer(text):
        end = m.end()
    return end
