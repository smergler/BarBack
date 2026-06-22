"""Tests for session-drinks verdict endpoint. DB is mocked."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock, call

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.session_drinks import _db, router

app = FastAPI()
app.include_router(router)
client = TestClient(app, raise_server_exceptions=False)

AUTH_HEADER = {"Authorization": "Bearer fake-jwt"}

DRINK = {
    "id": "d1",
    "session_id": "s1",
    "name": "Boulevardier",
    "ingredients": [
        {"name": "Four Roses Bourbon", "quantity": "1.5 oz", "source": "inventory"},
        {"name": "Sweet Vermouth", "quantity": "1 oz", "source": "pantry"},
    ],
    "steps": ["Stir", "Strain"],
    "why": "Spirit-forward.",
    "verdict": "liked",
    "created_at": "2026-01-01T00:00:00+00:00",
}
SESSION = {
    "id": "s1",
    "occasion": "movie night",
    "mood": "cozy",
    "created_at": "2026-01-01T00:00:00+00:00",
    "ended_at": None,
    "session_companions": [{"companion_id": "c1"}],
}
BOTTLE = {
    "id": "bot1",
    "name": "Four Roses Bourbon",
    "category": "bourbon",
    "subcategory": None,
    "is_active": True,
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}


def _mock_db(drink=None, session=None, bottles=None):
    db = MagicMock()
    db.set_verdict.return_value = drink
    db.get_session.return_value = session
    db.list_bottles.return_value = bottles or []
    return db


@contextlib.contextmanager
def _db_override(db):
    app.dependency_overrides[_db] = lambda: db
    try:
        yield
    finally:
        app.dependency_overrides.clear()


def test_verdict_requires_auth():
    resp = client.patch("/session-drinks/d1/verdict", json={"verdict": "liked"})
    assert resp.status_code in (401, 403)


def test_verdict_not_found():
    db = _mock_db(drink=None)
    with _db_override(db):
        resp = client.patch("/session-drinks/bad-id/verdict",
                            json={"verdict": "neutral"}, headers=AUTH_HEADER)
    assert resp.status_code == 404


def test_verdict_neutral_no_rpc():
    """neutral verdict must not trigger any companion RPC calls."""
    neutral_drink = {**DRINK, "verdict": "neutral"}
    db = _mock_db(drink=neutral_drink, session=SESSION, bottles=[BOTTLE])
    with _db_override(db):
        resp = client.patch("/session-drinks/d1/verdict",
                            json={"verdict": "neutral"}, headers=AUTH_HEADER)
    assert resp.status_code == 200
    db.upsert_companion_like.assert_not_called()
    db.upsert_companion_dislike.assert_not_called()


def test_verdict_liked_calls_rpc():
    """liked verdict fires upsert_companion_like for each companion × category."""
    db = _mock_db(drink=DRINK, session=SESSION, bottles=[BOTTLE])
    with _db_override(db):
        resp = client.patch("/session-drinks/d1/verdict",
                            json={"verdict": "liked"}, headers=AUTH_HEADER)
    assert resp.status_code == 200
    db.upsert_companion_like.assert_called_once_with("c1", "bourbon")
    db.upsert_companion_dislike.assert_not_called()


def test_verdict_disliked_calls_rpc():
    """disliked verdict fires upsert_companion_dislike."""
    disliked_drink = {**DRINK, "verdict": "disliked"}
    db = _mock_db(drink=disliked_drink, session=SESSION, bottles=[BOTTLE])
    with _db_override(db):
        resp = client.patch("/session-drinks/d1/verdict",
                            json={"verdict": "disliked"}, headers=AUTH_HEADER)
    assert resp.status_code == 200
    db.upsert_companion_dislike.assert_called_once_with("c1", "bourbon")
    db.upsert_companion_like.assert_not_called()


def test_verdict_no_inventory_ingredients_no_rpc():
    """If no ingredients are sourced from inventory, skip RPC calls."""
    pantry_only_drink = {
        **DRINK,
        "ingredients": [{"name": "Simple Syrup", "quantity": "0.5 oz", "source": "pantry"}],
    }
    db = _mock_db(drink=pantry_only_drink, session=SESSION, bottles=[BOTTLE])
    with _db_override(db):
        resp = client.patch("/session-drinks/d1/verdict",
                            json={"verdict": "liked"}, headers=AUTH_HEADER)
    assert resp.status_code == 200
    db.upsert_companion_like.assert_not_called()


def test_verdict_no_companions_no_rpc():
    """If session has no companions, skip RPC calls."""
    session_no_companions = {**SESSION, "session_companions": []}
    db = _mock_db(drink=DRINK, session=session_no_companions, bottles=[BOTTLE])
    with _db_override(db):
        resp = client.patch("/session-drinks/d1/verdict",
                            json={"verdict": "liked"}, headers=AUTH_HEADER)
    assert resp.status_code == 200
    db.upsert_companion_like.assert_not_called()


def test_verdict_liked_unmatched_ingredient_no_rpc():
    """inventory ingredient that doesn't match any bottle → no RPC calls."""
    unmatched_drink = {
        **DRINK,
        "ingredients": [{"name": "Mystery Spirit", "quantity": "1 oz", "source": "inventory"}],
    }
    db = _mock_db(drink=unmatched_drink, session=SESSION, bottles=[BOTTLE])
    with _db_override(db):
        resp = client.patch("/session-drinks/d1/verdict",
                            json={"verdict": "liked"}, headers=AUTH_HEADER)
    assert resp.status_code == 200
    db.upsert_companion_like.assert_not_called()


def test_verdict_invalid_value():
    """Reject unknown verdict values."""
    db = _mock_db(drink=DRINK)
    with _db_override(db):
        resp = client.patch("/session-drinks/d1/verdict",
                            json={"verdict": "meh"}, headers=AUTH_HEADER)
    assert resp.status_code == 422
