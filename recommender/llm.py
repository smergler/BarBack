from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class LLMClient(Protocol):
    def generate(self, system: str, user: str) -> str:
        """Return the model's raw text response (expected to be JSON)."""
        ...


@dataclass
class UsageStats:
    input_tokens: int
    output_tokens: int


class MockClient:
    """Returns canned responses keyed by scenario id. Lets the full pipeline +
    eval run offline with zero token spend."""

    def __init__(self, responses: dict[str, str], key: str):
        self._responses = responses
        self._key = key

    def generate(self, system: str, user: str) -> str:  # noqa: ARG002
        if self._key not in self._responses:
            raise KeyError(f"No mock response for scenario {self._key!r}")
        return self._responses[self._key]


class AnthropicClient:
    """Live client that calls the Anthropic Messages API.

    `temperature` support varies by model and by installed `anthropic` SDK
    version (some releases drop it from `Messages.create()`'s signature
    entirely; some models reject it server-side). Rather than hardcoding a
    model-name denylist that goes stale every time either side changes, we
    detect rejection on first use and stop sending it for the rest of this
    client's lifetime.
    """

    DEFAULT_MODEL = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ):
        self._api_key = api_key
        self._model = model or self.DEFAULT_MODEL
        self._max_tokens = max_tokens
        self._temperature = temperature
        self._supports_temperature = True
        self.last_usage: UsageStats | None = None

    def _base_params(self) -> dict[str, Any]:
        params: dict[str, Any] = {"model": self._model, "max_tokens": self._max_tokens}
        if self._supports_temperature:
            params["temperature"] = self._temperature
        return params

    def _create(self, client: Any, **kwargs: Any) -> Any:
        from anthropic import BadRequestError

        try:
            return client.messages.create(**self._base_params(), **kwargs)
        except (TypeError, BadRequestError) as e:
            msg = str(e)
            is_temperature_error = "temperature" in msg and (
                "unexpected keyword" in msg or "Extra inputs" in msg or "unsupported" in msg.lower()
            )
            if not self._supports_temperature or not is_temperature_error:
                raise
            self._supports_temperature = False
            return client.messages.create(**self._base_params(), **kwargs)

    def generate(self, system: str, user: str) -> str:
        from anthropic import Anthropic  # lazy import; optional dependency

        client = Anthropic(api_key=self._api_key)
        msg = self._create(client, system=system, messages=[{"role": "user", "content": user}])
        self.last_usage = UsageStats(
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
        )
        return msg.content[0].text

    def generate_structured(self, system: str, user: str, schema: dict[str, Any]) -> str:
        """Generate with output_config.format for guaranteed-valid JSON matching schema."""
        from anthropic import Anthropic  # lazy import; optional dependency

        client = Anthropic(api_key=self._api_key)
        msg = self._create(
            client,
            system=system,
            messages=[{"role": "user", "content": user}],
            output_config={"format": {"type": "json_schema", "schema": schema}},
        )
        self.last_usage = UsageStats(
            input_tokens=msg.usage.input_tokens,
            output_tokens=msg.usage.output_tokens,
        )
        return msg.content[0].text
