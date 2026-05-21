import os

import pytest

yaml = pytest.importorskip("yaml")

from src import prompts  # noqa: E402  -- import after the PyYAML guard


@pytest.fixture
def domain_dirs(tmp_path, monkeypatch):
    """Route each domain to its own subdirectory under ``tmp_path``.

    Mirrors the on-disk layout where each domain has its own folder, so
    cross-domain isolation can be exercised in a single test if needed.
    """
    def _dir_for(domain):
        d = tmp_path / domain
        return str(d)

    monkeypatch.setattr(prompts, "_prompts_dir", _dir_for)
    return tmp_path


@pytest.fixture
def recaption_dir(domain_dirs):
    """Convenience: the recaption subdir."""
    return domain_dirs / "recaption"


def _write_yaml(path, data):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        yaml.safe_dump(data, fh, sort_keys=False, allow_unicode=True)


def test_seed_defaults_for_domain_creates_files(domain_dirs):
    prompts.seed_defaults("recaption")
    rec = domain_dirs / "recaption"
    assert (rec / "stable_diffusion.yml").exists()
    assert (rec / "flux.yml").exists()
    sd = yaml.safe_load((rec / "stable_diffusion.yml").read_text())
    assert sd["name"] == "Stable Diffusion"
    assert "comma-separated tag list" in sd["system_prompt"]


def test_seed_defaults_all_domains(domain_dirs):
    prompts.seed_defaults()  # no argument -> every domain
    assert (domain_dirs / "recaption" / "stable_diffusion.yml").exists()
    assert (domain_dirs / "recaption" / "flux.yml").exists()
    assert (domain_dirs / "prompt_enhancer" / "stable_diffusion.yml").exists()
    assert (domain_dirs / "prompt_enhancer" / "flux.yml").exists()
    # Each domain seeds its own text.
    rec_sd = yaml.safe_load(
        (domain_dirs / "recaption" / "stable_diffusion.yml").read_text()
    )
    enh_sd = yaml.safe_load(
        (domain_dirs / "prompt_enhancer" / "stable_diffusion.yml").read_text()
    )
    assert rec_sd["system_prompt"] != enh_sd["system_prompt"]
    assert "captioner" in rec_sd["system_prompt"]
    assert "prompt enhancer" in enh_sd["system_prompt"]


def test_seed_defaults_preserves_user_edits(domain_dirs):
    prompts.seed_defaults("recaption")
    edited = {"name": "Custom Flux", "system_prompt": "I am unique."}
    _write_yaml(str(domain_dirs / "recaption" / "flux.yml"), edited)
    prompts.seed_defaults("recaption")
    reloaded = yaml.safe_load((domain_dirs / "recaption" / "flux.yml").read_text())
    assert reloaded == edited


def test_seed_defaults_creates_missing_parent(tmp_path, monkeypatch):
    nested = tmp_path / "default" / "coras_textgen" / "prompts"

    def _dir_for(domain):
        return str(nested / domain)

    monkeypatch.setattr(prompts, "_prompts_dir", _dir_for)
    prompts.seed_defaults("prompt_enhancer")
    assert (nested / "prompt_enhancer" / "stable_diffusion.yml").exists()


def test_seed_unknown_domain_noop(domain_dirs):
    prompts.seed_defaults("not_a_real_domain")
    # No files should be created anywhere.
    assert not any((domain_dirs / "not_a_real_domain").glob("*")) if (
        domain_dirs / "not_a_real_domain"
    ).exists() else True


def test_list_styles_returns_sorted(recaption_dir):
    os.makedirs(recaption_dir, exist_ok=True)
    _write_yaml(str(recaption_dir / "z.yml"), {"name": "Zebra", "system_prompt": "z"})
    _write_yaml(str(recaption_dir / "a.yml"), {"name": "Alpaca", "system_prompt": "a"})
    styles = prompts.list_styles("recaption")
    assert [s["name"] for s in styles] == ["Alpaca", "Zebra"]
    assert [s["filename"] for s in styles] == ["a.yml", "z.yml"]


def test_list_styles_skips_invalid_files(recaption_dir):
    os.makedirs(recaption_dir, exist_ok=True)
    _write_yaml(str(recaption_dir / "ok.yml"), {"name": "Good", "system_prompt": "g"})
    _write_yaml(str(recaption_dir / "noname.yml"), {"system_prompt": "g"})
    _write_yaml(str(recaption_dir / "blank.yml"), {"name": "   ", "system_prompt": "g"})
    _write_yaml(str(recaption_dir / "intname.yml"), {"name": 42, "system_prompt": "g"})
    _write_yaml(str(recaption_dir / "noprompt.yml"), {"name": "X"})
    _write_yaml(str(recaption_dir / "list.yml"), ["not", "a", "dict"])
    (recaption_dir / "bad.yml").write_text("not: valid: yaml: :")
    styles = prompts.list_styles("recaption")
    assert [s["name"] for s in styles] == ["Good"]


def test_list_styles_collision_first_filename_wins(recaption_dir):
    os.makedirs(recaption_dir, exist_ok=True)
    _write_yaml(str(recaption_dir / "a_dupe.yml"), {"name": "Dup", "system_prompt": "first"})
    _write_yaml(str(recaption_dir / "b_dupe.yml"), {"name": "Dup", "system_prompt": "second"})
    styles = prompts.list_styles("recaption")
    assert len(styles) == 1
    assert styles[0]["filename"] == "a_dupe.yml"


def test_list_styles_handles_missing_dir(domain_dirs):
    # domain_dirs creates tmp_path but no per-domain subdir until seeded.
    assert prompts.list_styles("recaption") == []


def test_list_styles_handles_none_dir(monkeypatch):
    monkeypatch.setattr(prompts, "_prompts_dir", lambda domain: None)
    assert prompts.list_styles("recaption") == []


def test_domains_are_isolated(domain_dirs):
    """Same display name in two domains is independent."""
    os.makedirs(domain_dirs / "recaption", exist_ok=True)
    os.makedirs(domain_dirs / "prompt_enhancer", exist_ok=True)
    _write_yaml(
        str(domain_dirs / "recaption" / "shared.yml"),
        {"name": "Shared", "system_prompt": "recaption body"},
    )
    _write_yaml(
        str(domain_dirs / "prompt_enhancer" / "shared.yml"),
        {"name": "Shared", "system_prompt": "enhancer body"},
    )
    assert prompts.get_system_prompt("recaption", "Shared") == "recaption body"
    assert prompts.get_system_prompt("prompt_enhancer", "Shared") == "enhancer body"


def test_get_system_prompt_returns_match(recaption_dir):
    os.makedirs(recaption_dir, exist_ok=True)
    _write_yaml(str(recaption_dir / "x.yml"), {"name": "Foo", "system_prompt": "hello"})
    assert prompts.get_system_prompt("recaption", "Foo") == "hello"
    assert prompts.get_system_prompt("recaption", "  Foo  ") == "hello"


def test_get_system_prompt_returns_none_for_unknown(recaption_dir):
    os.makedirs(recaption_dir, exist_ok=True)
    _write_yaml(str(recaption_dir / "x.yml"), {"name": "Foo", "system_prompt": "hello"})
    assert prompts.get_system_prompt("recaption", "Bar") is None


def test_get_system_prompt_rejects_blank(recaption_dir):
    os.makedirs(recaption_dir, exist_ok=True)
    assert prompts.get_system_prompt("recaption", "") is None
    assert prompts.get_system_prompt("recaption", "   ") is None
    assert prompts.get_system_prompt("recaption", None) is None


def test_get_system_prompt_handles_missing_dir(domain_dirs):
    assert prompts.get_system_prompt("recaption", "Anything") is None


def test_yaml_extension_variants(recaption_dir):
    os.makedirs(recaption_dir, exist_ok=True)
    _write_yaml(str(recaption_dir / "lower.yaml"), {"name": "Lower", "system_prompt": "x"})
    _write_yaml(str(recaption_dir / "MixedCase.YML"), {"name": "Mixed", "system_prompt": "x"})
    (recaption_dir / "ignored.txt").write_text("should not load")
    names = [s["name"] for s in prompts.list_styles("recaption")]
    assert "Lower" in names
    assert "Mixed" in names
