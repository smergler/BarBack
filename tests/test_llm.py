from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from recommender.llm import AnthropicClient, MockClient


def _msg(text="{}"):
    return SimpleNamespace(
        content=[SimpleNamespace(text=text)],
        usage=SimpleNamespace(input_tokens=11, output_tokens=7),
    )


def test_mock_client_returns_canned_and_raises_on_unknown_key():
    assert MockClient({"a": "x"}, "a").generate("s", "u") == "x"
    with pytest.raises(KeyError):
        MockClient({}, "missing").generate("s", "u")


def test_base_params_includes_temperature_until_disabled():
    c = AnthropicClient(temperature=0.5)
    assert c._base_params()["temperature"] == 0.5
    c._supports_temperature = False
    assert "temperature" not in c._base_params()


def test_create_retries_without_temperature_on_api_shaped_error():
    c = AnthropicClient()
    sdk = MagicMock()
    sdk.messages.create.side_effect = [TypeError("unexpected keyword argument 'temperature'"), _msg()]
    c._create(sdk, system="s", messages=[])
    assert c._supports_temperature is False
    assert "temperature" not in sdk.messages.create.call_args_list[1].kwargs


def test_create_does_not_retry_when_temperature_only_appears_in_message():
    c = AnthropicClient()
    sdk = MagicMock()
    sdk.messages.create.side_effect = TypeError("bad prompt mentions temperature")
    with pytest.raises(TypeError):
        c._create(sdk, system="s", messages=[])
    assert c._supports_temperature is True
    assert sdk.messages.create.call_count == 1


def test_create_reraises_if_temperature_already_disabled():
    c = AnthropicClient()
    c._supports_temperature = False
    sdk = MagicMock()
    sdk.messages.create.side_effect = TypeError("unexpected keyword argument 'temperature'")
    with pytest.raises(TypeError):
        c._create(sdk, system="s", messages=[])


def test_generate_records_usage_and_returns_text():
    c = AnthropicClient()
    with patch("anthropic.Anthropic") as anth:
        anth.return_value.messages.create.return_value = _msg("hello")
        assert c.generate("sys", "usr") == "hello"
    assert (c.last_usage.input_tokens, c.last_usage.output_tokens) == (11, 7)


def test_generate_structured_passes_schema():
    c = AnthropicClient()
    with patch("anthropic.Anthropic") as anth:
        create = anth.return_value.messages.create
        create.return_value = _msg("{}")
        assert c.generate_structured("sys", "usr", {"type": "object"}) == "{}"
    fmt = create.call_args.kwargs["output_config"]["format"]
    assert fmt == {"type": "json_schema", "schema": {"type": "object"}}
