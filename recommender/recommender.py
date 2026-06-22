from __future__ import annotations

import json

from pydantic import ValidationError

from .context import SYSTEM_PROMPT, build_context
from .llm import LLMClient
from .schemas import Bottle, Recommendation, RecommendRequest


class RecommendationError(Exception):
    pass


def recommend(
    req: RecommendRequest, inventory: list[Bottle], llm: LLMClient
) -> Recommendation:
    user_msg = build_context(req, inventory)
    raw = llm.generate(SYSTEM_PROMPT, user_msg)
    try:
        return _parse(raw)
    except (json.JSONDecodeError, ValidationError):
        # one corrective retry before giving up
        retry_msg = (
            user_msg
            + "\n\nYour previous reply was not valid JSON. Respond with ONLY the JSON object."
        )
        raw = llm.generate(SYSTEM_PROMPT, retry_msg)
        try:
            return _parse(raw)
        except (json.JSONDecodeError, ValidationError) as e:
            raise RecommendationError(f"Model did not return valid JSON: {e}") from e


def _parse(raw: str) -> Recommendation:
    raw = raw.strip()
    if raw.startswith("```"):  # tolerate ```json fences
        raw = raw.split("```", 2)[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()
    data = json.loads(raw)
    return Recommendation.model_validate(data)
