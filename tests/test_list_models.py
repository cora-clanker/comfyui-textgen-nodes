from unittest.mock import patch

import pytest
import requests

from src.client import list_models
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


class _Resp:
    def __init__(self, *, status=200, payload=None, text="ok"):
        self.status_code = status
        self.ok = 200 <= status < 300
        self._payload = payload
        self.text = text

    def json(self):
        if isinstance(self._payload, Exception):
            raise self._payload
        return self._payload


def test_parses_openai_response():
    payload = {"data": [{"id": "b"}, {"id": "a"}, {"id": "c"}]}
    with patch("src.client.requests.get", return_value=_Resp(payload=payload)):
        assert list_models(_cfg()) == ["a", "b", "c"]


def test_dedupes_ids():
    payload = {"data": [{"id": "a"}, {"id": "a"}, {"id": "b"}]}
    with patch("src.client.requests.get", return_value=_Resp(payload=payload)):
        assert list_models(_cfg()) == ["a", "b"]


def test_skips_malformed_entries():
    payload = {
        "data": [
            {"id": "good"},
            {"id": ""},
            {"id": None},
            "not-a-dict",
            {"no_id": "x"},
        ]
    }
    with patch("src.client.requests.get", return_value=_Resp(payload=payload)):
        assert list_models(_cfg()) == ["good"]


def test_missing_data_field_returns_empty():
    with patch("src.client.requests.get", return_value=_Resp(payload={})):
        assert list_models(_cfg()) == []


def test_non_object_response_returns_empty():
    with patch("src.client.requests.get", return_value=_Resp(payload=["a", "b"])):
        assert list_models(_cfg()) == []


def test_http_error_raises():
    resp = _Resp(status=401, payload={}, text="bad key")
    with patch("src.client.requests.get", return_value=resp):
        with pytest.raises(RuntimeError, match="HTTP 401"):
            list_models(_cfg())


def test_transport_error_raises():
    with patch(
        "src.client.requests.get",
        side_effect=requests.ConnectionError("boom"),
    ):
        with pytest.raises(RuntimeError, match="failed"):
            list_models(_cfg())
