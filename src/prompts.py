"""Prompt-style storage for the Recaption node.

Styles live as YAML files under ``<user_dir>/default/coras_textgen/prompts/
recaption/`` and are user-editable. Each file has ``name`` (display label shown
in the dropdown) and ``system_prompt`` (the actual instruction sent to the
model). On extension load we seed two defaults (Stable Diffusion / Flux) if
they are missing, but we never clobber an existing file -- users can edit the
seeded prompts or add their own without losing changes across restarts.

All public functions are deliberately defensive (mirroring ``config.py``): any
filesystem, YAML, or import failure collapses to an empty-or-None return and a
warning, never an exception, so a malformed YAML file cannot break the
dropdown route or the executor.
"""

import logging
import os

_logger = logging.getLogger(__name__)


_STABLE_DIFFUSION_PROMPT = """\
You are an image-to-prompt captioner for tag-based Stable Diffusion models (SD 1.5, SDXL, Pony, Illustrious, NoobAI). Given an image, output a single comma-separated tag list that would reproduce it. Output ONLY the tag list — no preamble, no explanation, no quotes.

Tag conventions:
- Lowercase, comma-separated, underscores allowed for multi-word concepts (e.g. long_hair, looking_at_viewer)
- Use Danbooru-style tags when the image is anime/illustration; use plain descriptive tags for photographic/realistic images
- No sentences, no articles (a/an/the), no conjunctions
- Roughly 25–50 tags total; densest information first, since earlier tags carry more weight

Order tags in this rough priority:
1. Medium and overall style (photograph, oil painting, 3d render, anime screencap, pixel art, watercolor, etc.)
2. Primary subject(s): count, gender/species, age descriptor (1girl, 2boys, solo, elderly man, tabby cat)
3. Subject attributes: hair color/length/style, eye color, expression, skin, build, distinctive features
4. Clothing and accessories, top to bottom
5. Pose, action, framing (sitting, walking, from above, dutch angle, close-up, full body, portrait)
6. Setting and environment (forest, kitchen, neon-lit alley, beach at sunset)
7. Background elements and props
8. Lighting (rim lighting, golden hour, harsh shadows, soft diffused light, backlit)
9. Color palette and mood (muted colors, vibrant, monochrome, warm tones)
10. Technical/render qualifiers only if visually evident (depth of field, bokeh, film grain, cel shading, chromatic aberration)
11. Artist or style reference tags only if the style is distinctly recognizable

Do not include:
- Quality boosters you cannot verify from the image (masterpiece, best quality, 8k, highly detailed) — only include them if the image genuinely exhibits that level of polish
- Speculation about what is off-frame
- Negative-prompt content
- Watermark/signature tags unless one is actually visible

Be specific over generic: "crimson velvet curtains" beats "red fabric"; "shoulder-length wavy auburn hair" beats "long hair". If you cannot determine something with confidence, leave it out rather than guess.
"""


_FLUX_PROMPT = """\
You are an image-to-prompt captioner for FLUX models (FLUX.1 dev, schnell, and derivatives). Given an image, output a single natural-language prompt that would reproduce it. Output ONLY the prompt — no preamble, no labels, no quotes, no bullet points.

Write in flowing prose, 2–5 sentences, roughly 60–180 words. FLUX responds to descriptive natural language the way a human would describe a scene to another human; it does not need tag soup or quality boosters.

Cover these elements, weaving them naturally rather than listing:
- Medium and style up front ("A photograph of...", "An oil painting depicting...", "A 3D render showing...", "A pen-and-ink illustration of...")
- The main subject with specific, concrete detail: appearance, clothing, expression, posture, what they are doing
- Spatial relationships and composition (foreground/background, what is to the left/right, framing such as close-up, wide shot, overhead, low angle)
- Setting and environment with sensory specifics
- Lighting: source, direction, quality, and resulting mood (warm afternoon light streaming through a window, harsh overhead fluorescents, soft overcast daylight, a single candle casting long shadows)
- Color palette and atmosphere
- For photographic images, include plausible camera details when the image clearly suggests them: lens character (shallow depth of field, wide-angle distortion, macro), film stock or digital look, grain, motion blur
- For illustrated or painted images, name the technique and any distinctive stylistic markers (visible brushstrokes, flat cel shading, crosshatching, halftone dots, watercolor bleeds)

Guidelines:
- Be concrete and specific. "A woman in a mustard-yellow wool coat" beats "a woman in a coat." "Late afternoon sun raking across the floorboards" beats "good lighting."
- Describe only what is visible. Do not invent narrative context, names, or backstory.
- Avoid empty intensifiers (stunning, beautiful, amazing, masterpiece, 8k, highly detailed). Replace them with the concrete features that would produce that impression.
- Do not use comma-separated tag lists. Use complete sentences.
- If the image contains legible text, quote it exactly within the prompt (e.g., a sign reading "OPEN 24 HOURS").
- If the style strongly resembles a known artist or medium and is visually unambiguous, you may name it; otherwise describe the style directly.
"""


_DEFAULTS = {
    "stable_diffusion.yml": {
        "name": "Stable Diffusion",
        "system_prompt": _STABLE_DIFFUSION_PROMPT,
    },
    "flux.yml": {
        "name": "Flux",
        "system_prompt": _FLUX_PROMPT,
    },
}


def _prompts_dir():
    """Absolute path to the recaption prompts directory, or ``None``.

    Returns ``None`` when not running inside ComfyUI (e.g. unit tests that
    don't monkeypatch this function).
    """
    try:
        import folder_paths  # provided by ComfyUI on sys.path

        base = folder_paths.get_user_directory()
    except Exception:
        return None
    return os.path.join(base, "default", "coras_textgen", "prompts", "recaption")


def _import_yaml():
    """Lazy import of PyYAML; returns the module or ``None`` if unavailable."""
    try:
        import yaml  # noqa: WPS433 -- defensive lazy import
        return yaml
    except ImportError:
        return None


def _load_yaml_file(path):
    """Load a YAML file as a dict; return ``None`` on any failure.

    Top-level YAML lists/scalars are treated as missing -- we only accept dicts
    so accessing ``name``/``system_prompt`` is safe upstream.
    """
    yaml = _import_yaml()
    if yaml is None:
        return None
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
    except (OSError, yaml.YAMLError):
        return None
    return data if isinstance(data, dict) else None


def seed_defaults():
    """Write default YAML files to the prompts dir if absent. Never raises.

    Idempotent: existing files are left untouched so user edits survive
    restarts. Called from ``CorasTextGenExtension.on_load``.
    """
    directory = _prompts_dir()
    if directory is None:
        return
    yaml = _import_yaml()
    if yaml is None:
        _logger.warning("coras_textgen: PyYAML unavailable; skipping prompt seeding.")
        return
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as exc:
        _logger.warning("coras_textgen: could not create %s: %s", directory, exc)
        return

    for filename, data in _DEFAULTS.items():
        path = os.path.join(directory, filename)
        if os.path.exists(path):
            continue
        try:
            # "x" mode = create-only; if a race created the file between the
            # exists() check and the open(), we don't clobber.
            with open(path, "x", encoding="utf-8") as fh:
                yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)
        except (OSError, FileExistsError) as exc:
            _logger.warning("coras_textgen: could not seed %s: %s", path, exc)


def list_styles():
    """Return ``[{"filename": ..., "name": ...}, ...]`` sorted by display name.

    Entries with a missing/blank ``name`` or ``system_prompt`` are skipped.
    On a ``name`` collision the file that sorts first by filename wins.
    """
    directory = _prompts_dir()
    if directory is None or not os.path.isdir(directory):
        return []

    try:
        filenames = sorted(os.listdir(directory))
    except OSError:
        return []

    seen_names = {}
    for filename in filenames:
        lower = filename.lower()
        if not (lower.endswith(".yml") or lower.endswith(".yaml")):
            continue
        data = _load_yaml_file(os.path.join(directory, filename))
        if not data:
            continue
        name = data.get("name")
        prompt = data.get("system_prompt")
        if not isinstance(name, str) or not name.strip():
            continue
        if not isinstance(prompt, str) or not prompt.strip():
            continue
        name = name.strip()
        if name in seen_names:
            _logger.warning(
                "coras_textgen: duplicate prompt-style name %r in %s (keeping %s)",
                name, filename, seen_names[name],
            )
            continue
        seen_names[name] = filename

    return sorted(
        ({"filename": fn, "name": nm} for nm, fn in seen_names.items()),
        key=lambda e: e["name"].lower(),
    )


def get_system_prompt(name):
    """Return the system prompt for the given display name, or ``None``."""
    if not isinstance(name, str) or not name.strip():
        return None
    target = name.strip()
    directory = _prompts_dir()
    if directory is None or not os.path.isdir(directory):
        return None

    try:
        filenames = sorted(os.listdir(directory))
    except OSError:
        return None

    for filename in filenames:
        lower = filename.lower()
        if not (lower.endswith(".yml") or lower.endswith(".yaml")):
            continue
        data = _load_yaml_file(os.path.join(directory, filename))
        if not data:
            continue
        entry_name = data.get("name")
        prompt = data.get("system_prompt")
        if (
            isinstance(entry_name, str)
            and entry_name.strip() == target
            and isinstance(prompt, str)
            and prompt.strip()
        ):
            return prompt
    return None
