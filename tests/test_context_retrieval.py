from types import SimpleNamespace
from unittest.mock import patch

from recommender import context
from recommender.context import build_context
from recommender.schemas import Bottle, CompanionProfile, RecommendRequest

INV = [
    Bottle(id="1", name="Four Roses", category="bourbon"),
    Bottle(id="2", name="Campari", category="liqueur", subcategory="amaro"),
]


def test_context_renders_optional_sections():
    req = RecommendRequest(
        occasion="party",
        mood="festive",
        available_perishables=["lime"],
        companions=[CompanionProfile(name="Ann", likes=["gin"], dislikes=[])],
        constraints=["no egg"],
        already_suggested=["Negroni"],
        session_feedback=[{"name": "Daiquiri", "verdict": "liked"}],
    )
    out = build_context(req, INV)
    for expected in ["Mood/vibe: festive", "Campari [liqueur / amaro]", "lime",
                     "Ann: likes gin; dislikes —", "Constraints: no egg",
                     "- Negroni", "- Daiquiri: liked"]:
        assert expected in out


def test_context_without_perishables_says_none_confirmed():
    assert "none confirmed" in build_context(RecommendRequest(occasion="x"), INV)


def test_retrieval_query_includes_mood_and_up_to_four_spirits():
    inv = [Bottle(id=str(i), name=f"Gin{i}", category="gin") for i in range(6)]
    q = context._retrieval_query(RecommendRequest(occasion="o", mood="m"), inv)
    assert q.startswith("o m with Gin0, Gin1, Gin2, Gin3") and "Gin4" not in q


def test_retrieval_appended_after_closing_fence():
    recipe = SimpleNamespace(name="Old Fashioned", ingredients=[
        {"name": "bourbon", "measure": "2 oz"}, {"name": "bitters"}])
    with patch.object(context, "_RETRIEVAL_AVAILABLE", True), \
         patch.object(context, "_search", create=True, return_value=[recipe]):
        out = build_context(RecommendRequest(occasion="x"), INV, use_retrieval=True)
    assert out.index("</user_data>") < out.index("Old Fashioned: bourbon (2 oz), bitters")
