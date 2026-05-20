import os

import pytest

yaml = pytest.importorskip("yaml")

from src import prompts  # noqa: E402  -- import after the PyYAML guard


@pytest.fixture
def prompts_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(prompts, "_prompts_dir", lambda: str(tmp_path))
    return tmp_path


def _write_yaml(path, data):
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)


def test_seed_defaults_creates_both_files(prompts_dir):
    prompts.seed_defaults()
    assert (prompts_dir / "stable_diffusion.yml").exists()
    assert (prompts_dir / "flux.yml").exists()
    sd = yaml.safe_load((prompts_dir / "stable_diffusion.yml").read_text())
    assert sd["name"] == "Stable Diffusion"
    assert "comma-separated tag list" in sd["system_prompt"]


def test_seed_defaults_preserves_user_edits(prompts_dir):
    prompts.seed_defaults()
    edited = {"name": "Custom Flux", "system_prompt": "I am unique."}
    _write_yaml(prompts_dir / "flux.yml", edited)
    prompts.seed_defaults()
    reloaded = yaml.safe_load((prompts_dir / "flux.yml").read_text())
    assert reloaded == edited


def test_seed_defaults_creates_missing_parent(tmp_path, monkeypatch):
    nested = tmp_path / "default" / "coras_textgen" / "prompts" / "recaption"
    monkeypatch.setattr(prompts, "_prompts_dir", lambda: str(nested))
    prompts.seed_defaults()
    assert (nested / "stable_diffusion.yml").exists()


def test_list_styles_returns_sorted(prompts_dir):
    _write_yaml(prompts_dir / "z.yml", {"name": "Zebra", "system_prompt": "z"})
    _write_yaml(prompts_dir / "a.yml", {"name": "Alpaca", "system_prompt": "a"})
    styles = prompts.list_styles()
    assert [s["name"] for s in styles] == ["Alpaca", "Zebra"]
    assert [s["filename"] for s in styles] == ["a.yml", "z.yml"]


def test_list_styles_skips_invalid_files(prompts_dir):
    _write_yaml(prompts_dir / "ok.yml", {"name": "Good", "system_prompt": "g"})
    _write_yaml(prompts_dir / "noname.yml", {"system_prompt": "g"})
    _write_yaml(prompts_dir / "blank.yml", {"name": "   ", "system_prompt": "g"})
    _write_yaml(prompts_dir / "intname.yml", {"name": 42, "system_prompt": "g"})
    _write_yaml(prompts_dir / "noprompt.yml", {"name": "X"})
    _write_yaml(prompts_dir / "list.yml", ["not", "a", "dict"])
    (prompts_dir / "bad.yml").write_text("not: valid: yaml: :")
    styles = prompts.list_styles()
    assert [s["name"] for s in styles] == ["Good"]


def test_list_styles_collision_first_filename_wins(prompts_dir):
    _write_yaml(prompts_dir / "a_dupe.yml", {"name": "Dup", "system_prompt": "first"})
    _write_yaml(prompts_dir / "b_dupe.yml", {"name": "Dup", "system_prompt": "second"})
    styles = prompts.list_styles()
    assert len(styles) == 1
    assert styles[0]["filename"] == "a_dupe.yml"


def test_list_styles_handles_missing_dir(tmp_path, monkeypatch):
    missing = tmp_path / "does_not_exist"
    monkeypatch.setattr(prompts, "_prompts_dir", lambda: str(missing))
    assert prompts.list_styles() == []


def test_list_styles_handles_none_dir(monkeypatch):
    monkeypatch.setattr(prompts, "_prompts_dir", lambda: None)
    assert prompts.list_styles() == []


def test_get_system_prompt_returns_match(prompts_dir):
    _write_yaml(prompts_dir / "x.yml", {"name": "Foo", "system_prompt": "hello"})
    assert prompts.get_system_prompt("Foo") == "hello"
    assert prompts.get_system_prompt("  Foo  ") == "hello"


def test_get_system_prompt_returns_none_for_unknown(prompts_dir):
    _write_yaml(prompts_dir / "x.yml", {"name": "Foo", "system_prompt": "hello"})
    assert prompts.get_system_prompt("Bar") is None


def test_get_system_prompt_rejects_blank(prompts_dir):
    assert prompts.get_system_prompt("") is None
    assert prompts.get_system_prompt("   ") is None
    assert prompts.get_system_prompt(None) is None


def test_get_system_prompt_handles_missing_dir(tmp_path, monkeypatch):
    monkeypatch.setattr(prompts, "_prompts_dir", lambda: str(tmp_path / "nope"))
    assert prompts.get_system_prompt("Anything") is None


def test_yaml_extension_variants(prompts_dir):
    _write_yaml(prompts_dir / "lower.yaml", {"name": "Lower", "system_prompt": "x"})
    _write_yaml(prompts_dir / "MixedCase.YML", {"name": "Mixed", "system_prompt": "x"})
    (prompts_dir / "ignored.txt").write_text("should not load")
    names = [s["name"] for s in prompts.list_styles()]
    assert "Lower" in names
    assert "Mixed" in names
