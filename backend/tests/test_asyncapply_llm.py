"""The single schema-constrained call: retries, errors, and fence tolerance."""

from dataclasses import replace
from types import SimpleNamespace

import httpx
import pytest
from openai import APIStatusError
from pydantic import BaseModel

from services.asyncapply import llm


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


pytestmark = pytest.mark.anyio


class Answer(BaseModel):
    ok: bool


def _completion(content: str):
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])


class FakeClient:
    """Stands in for AsyncOpenAI, replaying a scripted list of replies."""

    def __init__(self, replies):
        self.replies = list(replies)
        self.calls = []
        self.chat = SimpleNamespace(completions=SimpleNamespace(create=self._create))

    async def _create(self, **kwargs):
        self.calls.append(kwargs)
        reply = self.replies.pop(0)
        if isinstance(reply, Exception):
            raise reply
        return _completion(reply)


@pytest.fixture
def no_sleep(monkeypatch):
    async def sleep(_seconds):
        return None

    monkeypatch.setattr(llm.asyncio, "sleep", sleep)


def _install(monkeypatch, replies) -> FakeClient:
    client = FakeClient(replies)
    monkeypatch.setattr(llm, "_client", lambda: client)
    return client


async def test_a_valid_reply_is_parsed(monkeypatch):
    _install(monkeypatch, ['{"ok": true}'])
    assert await llm.ask("evaluate_job", "sys", "usr", Answer) == Answer(ok=True)


async def test_the_schema_and_provider_pin_are_both_sent(monkeypatch):
    client = _install(monkeypatch, ['{"ok": true}'])
    await llm.ask("evaluate_job", "sys", "usr", Answer)
    call = client.calls[0]
    assert call["response_format"]["json_schema"]["strict"] is True
    assert call["extra_body"] == llm.REQUEST_EXTRAS
    # No tool loop: nothing may offer the model tools.
    assert "tools" not in call


async def test_a_fenced_reply_is_still_parsed(monkeypatch):
    _install(monkeypatch, ['```json\n{"ok": true}\n```'])
    assert await llm.ask("evaluate_job", "sys", "usr", Answer) == Answer(ok=True)


async def test_prose_is_a_failure(monkeypatch, no_sleep):
    _install(monkeypatch, ["I think the answer is yes."] * 3)
    with pytest.raises(llm.AgentError):
        await llm.ask("evaluate_job", "sys", "usr", Answer)


async def test_a_bad_reply_is_retried(monkeypatch, no_sleep):
    client = _install(monkeypatch, ["not json", '{"ok": false}'])
    assert await llm.ask("evaluate_job", "sys", "usr", Answer) == Answer(ok=False)
    assert len(client.calls) == 2


async def test_an_http_error_reports_its_status(monkeypatch, no_sleep):
    err = APIStatusError(
        "rate limited",
        response=httpx.Response(429, request=httpx.Request("POST", "https://openrouter.ai")),
        body=None,
    )
    _install(monkeypatch, [err] * 3)
    with pytest.raises(llm.AgentError, match="429"):
        await llm.ask("evaluate_job", "sys", "usr", Answer)


async def test_a_missing_key_is_named(monkeypatch):
    settings = llm.get_settings()
    monkeypatch.setattr(llm, "get_settings", lambda: replace(settings, openrouter_api_key=""))
    with pytest.raises(llm.AgentError, match="OPENROUTER_API_KEY"):
        await llm.ask("evaluate_job", "sys", "usr", Answer)


async def test_usage_is_recorded_inside_track_usage(monkeypatch):
    from types import SimpleNamespace as NS

    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
        usage=NS(total_tokens=500, cost=0.002),
    )

    async def create(**kwargs):
        return completion

    client = SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=create)))
    monkeypatch.setattr(llm, "_client", lambda: client)

    with llm.track_usage() as usage:
        await llm.ask("evaluate_job", "sys", "usr", Answer)

    assert usage.total_tokens == 500
    assert usage.total_cost_usd == 0.002


async def test_usage_outside_track_usage_is_a_no_op(monkeypatch):
    from types import SimpleNamespace as NS

    completion = SimpleNamespace(
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
        usage=NS(total_tokens=10, cost=0.0001),
    )
    _install(monkeypatch, [completion.choices[0].message.content])
    # No track_usage() block active: must not raise even though nothing collects it.
    assert await llm.ask("evaluate_job", "sys", "usr", Answer) == Answer(ok=True)


async def test_multiple_calls_inside_one_block_sum():
    from types import SimpleNamespace as NS

    completion = lambda cost, tokens: SimpleNamespace(  # noqa: E731
        choices=[SimpleNamespace(message=SimpleNamespace(content='{"ok": true}'))],
        usage=NS(total_tokens=tokens, cost=cost),
    )

    with llm.track_usage() as usage:
        llm._record_usage("extract_jd", completion(0.001, 100))
        llm._record_usage("evaluate_job", completion(0.003, 300))

    assert usage.total_tokens == 400
    assert usage.total_cost_usd == pytest.approx(0.004)


async def test_a_validation_error_shows_the_model_its_mistake_before_retrying(monkeypatch, no_sleep):
    """Live failure: two real postings failed identically on all 3 attempts
    because the retry resent an unchanged prompt. The model must see its own
    bad reply and the exact error, not just get asked again blindly."""
    bad = '{"ok": "not-a-boolean"}'
    good = '{"ok": true}'
    client = _install(monkeypatch, [bad, good])

    result = await llm.ask("evaluate_job", "sys", "usr", Answer)

    assert result == Answer(ok=True)
    second_call = client.calls[1]
    messages = second_call["messages"]
    assert messages[-2] == {"role": "assistant", "content": bad}
    assert "did not match the required schema" in messages[-1]["content"]
