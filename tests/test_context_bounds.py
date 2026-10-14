import pytest
from pydantic import ValidationError

from recommender.context import build_context
from recommender.recommender import RecommendationError
from recommender.schemas import Bottle, CompanionProfile, RecommendRequest

INV = [Bottle(id="1", name="Four Roses Small Batch", category="bourbon")]


def test_over_20_constraints_rejected_by_validation():
    with pytest.raises(ValidationError):
        RecommendRequest(occasion="nightcap", constraints=["no citrus"] * 25)


def test_build_context_raises_when_total_size_exceeds_20000():
    # constraints/available_perishables items are each capped at 100 chars, so
    # the field that can still push total context size past 20,000 without
    # tripping any Pydantic bound is a companion's likes/dislikes, whose list
    # length is capped (max_length=20) but whose individual string length is not.
    req = RecommendRequest(
        occasion="nightcap",
        constraints=["no citrus"] * 19,
        companions=[
            CompanionProfile(name="Dana", likes=["x" * 2000] * 20),
        ],
    )
    with pytest.raises(RecommendationError):
        build_context(req, INV)
