from unittest.mock import patch

from src.client import _is_vision_model, list_vision_models
from src.config import TextGenConfig


def _cfg():
    return TextGenConfig(
        api_base="https://example.test/v1",
        api_key="k",
        model="m",
        system_prompt="s",
        temperature=0.0,
        timeout=1.0,
    )


def test_heuristic_matches_each_keyword():
    keywords = [
        "qwen2-vl-7b",
        "Qwen2.5-VL-72B-Instruct",
        "llava-next-7b",
        "LLaVA-1.6",
        "gpt-4o",
        "gpt-4o-mini",
        "gemma-3-27b",
        "internvl-chat-v1-5",
        "MiniCPM-V-2_6",
        "pixtral-12b",
        "molmo-7b-d",
        "claude-3-5-sonnet",
        "kimi-vl-thinking",
        "some-vision-model",
    ]
    for k in keywords:
        assert _is_vision_model(k), k


def test_heuristic_rejects_text_only():
    for k in ["llama-3-70b", "mistral-7b", "phi-3-mini", "gpt-3.5-turbo", "mixtral"]:
        assert not _is_vision_model(k), k


def test_heuristic_handles_non_strings():
    assert _is_vision_model(None) is False
    assert _is_vision_model(42) is False


def test_list_vision_models_filters_by_default():
    pool = ["gpt-4o", "llama-3-8b", "qwen2-vl-7b", "mistral-7b"]
    with patch("src.client.list_models", return_value=pool):
        assert list_vision_models(_cfg()) == ["gpt-4o", "qwen2-vl-7b"]


def test_list_vision_models_passthrough_when_disabled():
    pool = ["gpt-4o", "llama-3-8b", "qwen2-vl-7b", "mistral-7b"]
    with patch("src.client.list_models", return_value=pool):
        assert list_vision_models(_cfg(), filter_vision=False) == pool


def test_list_vision_models_empty_input():
    with patch("src.client.list_models", return_value=[]):
        assert list_vision_models(_cfg()) == []
