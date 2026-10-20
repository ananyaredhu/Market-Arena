import pytest
from pydantic import BaseModel

from backend.common import llm
from backend.common.contracts import AgentExplain


class Answer(BaseModel):
    ok: bool


@pytest.fixture(autouse=True)
def clean(monkeypatch, tmp_path):
    monkeypatch.setattr(llm, "CACHE_DIR", tmp_path)
    llm._cooldown_until.clear()
    monkeypatch.setenv("LLM_MODE", "live")
    monkeypatch.setenv("GROQ_API_KEY", "k1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "k2")
    monkeypatch.setenv("LLM_PROVIDER_ORDER", "groq,openrouter")


def test_mock_mode_returns_fixture(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    out = llm.complete_json("agent_explain", "x", AgentExplain)
    assert out.agent_id == "a055"


def test_mock_unknown_task_raises(monkeypatch):
    monkeypatch.setenv("LLM_MODE", "mock")
    with pytest.raises(llm.LLMError):
        llm.complete_json("nope", "x", Answer)


def test_falls_back_to_second_provider_when_first_fails():
    calls = []

    def transport(p, messages, timeout):
        calls.append(p.name)
        if p.name == "groq":
            raise TimeoutError
        return {"text": '{"ok": true}', "usage": {}}

    assert llm.complete_json("t", "p", Answer, transport=transport).ok
    assert calls == ["groq", "openrouter"]


def test_failed_provider_is_skipped_during_cooldown():
    calls = []

    def transport(p, messages, timeout):
        calls.append(p.name)
        if p.name == "groq":
            raise TimeoutError
        return {"text": '{"ok": true}', "usage": {}}

    llm.complete_json("t1", "p", Answer, transport=transport)
    calls.clear()
    llm.complete_json("t2", "p", Answer, transport=transport)
    assert calls == ["openrouter"]


def test_invalid_json_is_retried_with_error_feedback():
    seen = []

    def transport(p, messages, timeout):
        seen.append(messages[-1]["content"])
        return {"text": "not json" if len(seen) == 1 else '{"ok": true}', "usage": {}}

    assert llm.complete_json("t", "p", Answer, transport=transport).ok
    assert len(seen) == 2 and seen[1].startswith("Invalid:")


def test_all_providers_fail_uses_fallback_then_raises():
    def boom(p, messages, timeout):
        raise TimeoutError

    assert llm.complete_json("t", "p", Answer, transport=boom, fallback=lambda: {"ok": False}).ok is False
    llm._cooldown_until.clear()
    with pytest.raises(llm.LLMError):
        llm.complete_json("t2", "p", Answer, transport=boom)


def test_cache_avoids_second_call():
    n = []

    def transport(p, messages, timeout):
        n.append(1)
        return {"text": '{"ok": true}', "usage": {}}

    llm.complete_json("t", "same", Answer, transport=transport)
    llm.complete_json("t", "same", Answer, transport=transport)
    assert len(n) == 1


# ---------------------------------------------------------------- provider quirks found with real models
class FakeResponse:
    def __init__(self, status: int, body: dict | str):
        self.status_code = status
        self.text = body if isinstance(body, str) else __import__("json").dumps(body)
        self._body = body

    def json(self):
        return self._body

    def raise_for_status(self):
        if self.status_code >= 400:
            raise llm.httpx.HTTPStatusError("error", request=None, response=self)


def ok_body(text: str) -> dict:
    return {"choices": [{"message": {"content": text}}], "usage": {}}


def test_a_provider_json_check_rejection_is_retried_without_json_mode(monkeypatch):
    """Groq's reasoning models sometimes return nothing usable in JSON mode (400 json_validate_failed)."""
    sent = []

    def fake_post(url, headers, json, timeout):
        sent.append("response_format" in json)
        if "response_format" in json:
            return FakeResponse(400, '{"error":{"code":"json_validate_failed","failed_generation":""}}')
        return FakeResponse(200, ok_body('{"ok": true}'))

    monkeypatch.setattr(llm.httpx, "post", fake_post)
    assert llm.complete_json("t", "p", Answer).ok is True
    assert sent == [True, False]  # first with JSON mode, then once without
    assert llm._cooldown_until == {}  # the provider was NOT parked as if it were down


def test_other_400_errors_still_fail_the_provider(monkeypatch):
    monkeypatch.setattr(llm.httpx, "post", lambda *a, **k: FakeResponse(400, '{"error":"bad request"}'))
    with pytest.raises(llm.LLMError):
        llm.complete_json("t", "p", Answer)
    assert "groq" in llm._cooldown_until


@pytest.mark.parametrize("reply", [
    '{"ok": true}',
    '```json\n{"ok": true}\n```',
    '```\n{"ok": true}\n```',
    'Sure, here is the JSON: {"ok": true} Hope that helps.',
])
def test_json_is_extracted_from_fenced_or_chatty_replies(reply):
    def transport(p, messages, timeout):
        return {"text": reply, "usage": {}}

    assert llm.complete_json("t", "p", Answer, transport=transport).ok is True


def test_an_empty_reply_is_a_validation_failure_not_a_crash():
    def transport(p, messages, timeout):
        return {"text": "", "usage": {}}

    with pytest.raises(llm.LLMError):
        llm.complete_json("t", "p", Answer, transport=transport)
