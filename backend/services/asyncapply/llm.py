"""One schema-constrained call to OpenRouter, retried, returning a typed object.

Every call also records its real cost. OpenRouter reports what the upstream
provider actually charged when `usage.include` is set -- no per-model price
table to keep in sync, just the number the provider billed for that request.

OpenRouter speaks the OpenAI chat-completions protocol, so this uses the openai
client directly: it generates a JSON schema from the stage's Pydantic model, has
the provider validate the reply against it, and hands back a typed object.

There is deliberately no tool loop. The stages gather what they need in Python
and pass it in, because every tool-use policy this pipeline has is a fixed
script, and a model handed a fixed script misexecutes it: offered tools
alongside a schema, deepseek-v3.2 answered without searching in 8 of 8 attempts
and invented the contact it was asked to find.
"""

import asyncio
import contextlib
import contextvars
from dataclasses import dataclass, field

from openai import APIError, APIStatusError, AsyncOpenAI
from openai.lib._pydantic import to_strict_json_schema
from pydantic import BaseModel, ValidationError

from services.asyncapply.settings import get_settings


@dataclass
class UsageLog:
    """What one item's worth of ask() calls actually cost."""

    entries: list[dict] = field(default_factory=list)

    @property
    def total_tokens(self) -> int:
        return sum(e["tokens"] for e in self.entries)

    @property
    def total_cost_usd(self) -> float:
        return sum(e["cost_usd"] for e in self.entries)


_usage_log: contextvars.ContextVar[UsageLog | None] = contextvars.ContextVar(
    "usage_log", default=None
)


@contextlib.contextmanager
def track_usage():
    """Collect the cost of every ask() call made inside this block.

    A contextvar rather than a threaded-through parameter, so the three stages
    (extract_jd, evaluate_job, find_contact) don't each need a cost argument
    just to pass it along. Safe under concurrent items: asyncio tasks each get
    their own copy of a contextvar.

    Yields:
        A UsageLog that fills in as calls complete inside the block.
    """
    log = UsageLog()
    token = _usage_log.set(log)
    try:
        yield log
    finally:
        _usage_log.reset(token)

# Worth retrying: the provider erred, or it returned something that did not
# match the schema it was given.
RETRYABLE = (APIError, ValidationError, ValueError, asyncio.TimeoutError)

# OpenRouter routes each request to whichever provider is cheapest, and they do
# not all honour the parameters sent. This makes routing skip any provider that
# does not support everything in the request, so a schema-constrained call only
# lands somewhere that enforces the schema.
REQUIRE_PARAMETERS = {"provider": {"require_parameters": True}}

# usage.include asks OpenRouter to report what the upstream provider actually
# billed for the request, in usage.cost -- the real number, not a model-price
# table computed from token counts that would drift as providers change.
REQUEST_EXTRAS = {**REQUIRE_PARAMETERS, "usage": {"include": True}}


def _record_usage(stage: str, completion) -> None:
    """Append one call's cost to the active track_usage() log, if any.

    Args:
        stage: The stage that made this call.
        completion: The provider's response, carrying `usage.cost` when
            REQUEST_EXTRAS was sent.
    """
    log = _usage_log.get()
    usage = getattr(completion, "usage", None)
    if log is None or usage is None:
        return
    log.entries.append(
        {
            "stage": stage,
            "tokens": usage.total_tokens or 0,
            "cost_usd": getattr(usage, "cost", None) or 0.0,
        }
    )


class AgentError(RuntimeError):
    """The provider failed, or never produced a usable answer."""


def _client() -> AsyncOpenAI:
    """Build the OpenRouter client.

    Returns:
        An async client pointed at the configured base URL.

    Raises:
        AgentError: if no API key is configured.
    """
    settings = get_settings()
    if not settings.openrouter_api_key:
        raise AgentError("OPENROUTER_API_KEY is not set; see the root README.")

    return AsyncOpenAI(
        api_key=settings.openrouter_api_key,
        base_url=settings.openrouter_base_url,
        timeout=settings.stage_timeout,
        max_retries=0,
    )


def _response_format(output: type[BaseModel]) -> dict:
    """Build the json_schema response_format for a stage's output model.

    Args:
        output: The stage's Pydantic output model.

    Returns:
        The response_format payload.
    """
    return {
        "type": "json_schema",
        "json_schema": {
            "name": output.__name__,
            "strict": True,
            "schema": to_strict_json_schema(output),
        },
    }


# Sent back to the model when its reply failed schema validation. Observed
# live: two real postings both failed all three attempts with the identical
# error (an enum field filled with a sentence, an object field filled with a
# plain string). Retrying with an unchanged prompt reproduces an unchanged
# mistake, so this shows the model its own bad reply next to the exact error
# instead of just asking again.
_CORRECTION_PROMPT = (
    "That reply did not match the required schema:\n{error}\n\n"
    "Reply again with corrected JSON that matches the schema exactly. An enum "
    "field must be set to one of its exact listed values, never a sentence "
    "explaining your reasoning. An object field (e.g. cover_letter, "
    "cv_tailoring) must be a JSON object with the fields the schema names, "
    "never a plain string."
)


def _unfence(content: str) -> str:
    """Strip a markdown code fence the model wrapped its JSON in.

    response_format=json_schema is meant to make this impossible. It was
    observed once anyway, and has not recurred in 128 sampled replies since
    REQUIRE_PARAMETERS narrowed routing. Kept because it is cheap and the
    alternative is failing a stage over a wrapper: only the fence is removed,
    so anything else that is not JSON is still a retryable failure.

    Args:
        content: The raw assistant message content.

    Returns:
        The content with any surrounding fence removed.
    """
    text = content.strip()
    if not text.startswith("```"):
        return text

    text = text.split("\n", 1)[-1] if "\n" in text else text
    return text.removesuffix("```").strip()


async def ask[Output: BaseModel](
    stage: str, system_prompt: str, user_prompt: str, output: type[Output]
) -> Output:
    """Ask the model one question and return its validated answer.

    Args:
        stage: Stage name, used to pick the model.
        system_prompt: Mode instructions plus any injected personal context.
        user_prompt: The task input, including anything already fetched for it.
        output: Pydantic model the reply must match.

    Returns:
        The parsed answer, as an instance of `output`.

    Raises:
        AgentError: if every attempt failed.
    """
    settings = get_settings()
    client = _client()
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ]

    last_error: Exception | None = None
    for attempt in range(1, settings.max_attempts + 1):
        content = None
        try:
            completion = await client.chat.completions.create(
                model=settings.models[stage],
                messages=messages,
                response_format=_response_format(output),
                extra_body=REQUEST_EXTRAS,
            )
            _record_usage(stage, completion)
            content = completion.choices[0].message.content
            if not content:
                raise ValueError("the model returned an empty answer")
            return output.model_validate_json(_unfence(content))

        except ValidationError as exc:
            last_error = exc
            messages.append({"role": "assistant", "content": content})
            messages.append({"role": "user", "content": _CORRECTION_PROMPT.format(error=exc)})
        except APIStatusError as exc:
            last_error = AgentError(f"provider returned {exc.status_code}: {str(exc)[:200]}")
        except RETRYABLE as exc:
            last_error = exc

        if attempt == settings.max_attempts:
            raise AgentError(
                f"{stage} failed after {attempt} attempts: {last_error}"
            ) from last_error
        await asyncio.sleep(2 ** (attempt - 1))

    raise AgentError("unreachable")
