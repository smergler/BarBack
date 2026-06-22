from __future__ import annotations

from typing import Protocol


class LLMClient(Protocol):
    def generate(self, system: str, user: str) -> str:
        """Return the model's raw text response (expected to be JSON)."""
        ...


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
    """Live client. Not exercised yet (no API key) — wired for later use."""

    MODEL = "claude-haiku-4-5-20251001"

    def __init__(
        self,
        api_key: str | None = None,
        max_tokens: int = 2000,
        temperature: float = 0.3,
    ):
        self._api_key = api_key
        self._max_tokens = max_tokens
        self._temperature = temperature

    def generate(self, system: str, user: str) -> str:
        from anthropic import Anthropic  # lazy import; optional dependency

        client = Anthropic(api_key=self._api_key)
        msg = client.messages.create(
            model=self.MODEL,
            max_tokens=self._max_tokens,
            temperature=self._temperature,
            system=system,
            messages=[{"role": "user", "content": user}],
        )
        return msg.content[0].text
