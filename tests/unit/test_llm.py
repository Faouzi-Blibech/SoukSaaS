import json
from types import SimpleNamespace

import litellm
import pytest
from pydantic import BaseModel

from app import llm
from app.config import settings


class Out(BaseModel):
    a: int
    b: str = "x"


@pytest.fixture(autouse=True)
def _reset():
    llm.reset_counts()
    yield
    llm.reset_counts()


def _fake(contents, calls):
    it = iter(contents)

    def completion(**kw):
        calls.append(kw)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=next(it)))])

    return completion


@pytest.fixture
def live(monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "live")
    monkeypatch.setattr(settings, "llm_api_key", "sk-test")


def test_mock_mode_never_calls_network(monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "mock")
    monkeypatch.setattr(litellm, "completion", lambda **k: pytest.fail("network used"))
    assert llm.chat("s", "u", task="t", mock=lambda: "hi") == "hi"
    assert llm.chat_json("s", "u", Out, task="t", mock=lambda: {"a": 1}) == Out(a=1)
    assert llm.chat_json("s", "u", Out, task="t", mock=lambda: Out(a=2)).a == 2
    assert llm.call_count["t"] == 3


def test_mock_invalid_raises(monkeypatch):
    monkeypatch.setattr(settings, "llm_mode", "mock")
    with pytest.raises(llm.LLMError):
        llm.chat_json("s", "u", Out, task="t", mock=lambda: {"a": "not-int"})


def test_live_valid_json(live, monkeypatch):
    calls = []
    monkeypatch.setattr(litellm, "completion", _fake([json.dumps({"a": 3})], calls))
    assert llm.chat_json("s", "u", Out, task="interest", mock=lambda: {"a": 0}).a == 3
    assert calls[0]["response_format"] == {"type": "json_object"}
    assert calls[0]["timeout"] == 20 and calls[0]["api_key"] == "sk-test"


def test_live_retry_then_success(live, monkeypatch):
    calls = []
    monkeypatch.setattr(litellm, "completion", _fake(["not json", json.dumps({"a": 1})], calls))
    assert llm.chat_json("s", "u", Out, task="t", mock=lambda: {"a": 0}).a == 1
    assert len(calls) == 2


def test_live_invalid_twice_raises(live, monkeypatch):
    calls = []
    monkeypatch.setattr(litellm, "completion", _fake(["{}", '{"a": "x"}', '{"a":1}'], calls))
    with pytest.raises(llm.LLMError):
        llm.chat_json("s", "u", Out, task="t", mock=lambda: {"a": 0})
    assert len(calls) == 2


def test_live_chat_provider_error_wrapped(live, monkeypatch):
    def boom(**kw):
        raise TimeoutError("slow")

    monkeypatch.setattr(litellm, "completion", boom)
    with pytest.raises(llm.LLMError):
        llm.chat("s", "u", task="t", mock=lambda: "x")


def test_load_product():
    assert llm.load_product().plans
