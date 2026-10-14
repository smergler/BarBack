"""Tests for the verdict endpoint's companion-feedback propagation."""

from __future__ import annotations

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app.main import app
from backend.auth import get_current_user
from backend.db import DB
from backend.routers.session_drinks import _db

client = TestClient(app, raise_server_exceptions=False)
AUTH_HEADER = {"Authorization": "Bearer fake-jwt"}

DRINK_ROW = {
    "id": "drink-1",
    "session_id": "s1",
    "ingredients": [{"name": "Four Roses Bourbon", "source": "inventory"}],
}
SESSION_WITH_FOREIGN_COMPANION = {
    "id": "s1",
    "session_companions": [{"companion_id": "c-foreign"}],
}
BOTTLE = {
    "id": "bot1", "name": "Four Roses Bourbon", "category": "bourbon",
    "subcategory": None,
}


def _mocked_db(**overrides) -> MagicMock:
    mock_db = MagicMock(spec=DB)
    mock_db.set_verdict.return_value = DRINK_ROW
    mock_db.get_session.return_value = SESSION_WITH_FOREIGN_COMPANION
    mock_db.list_bottles.return_value = [BOTTLE]
    for name, value in overrides.items():
        setattr(mock_db, name, value)
    return mock_db


def test_verdict_survives_rejected_companion_feedback_rpc():
    """upsert_companion_like raising (e.g. a legacy foreign session_companions row
    rejected by the ownership guard) must not turn a successful verdict write
    into a 500 — _apply_feedback should swallow it and set_verdict still 200s."""
    mock_db = _mocked_db()
    mock_db.upsert_companion_like.side_effect = Exception("insufficient_privilege")

    app.dependency_overrides[get_current_user] = lambda: "user-1"
    app.dependency_overrides[_db] = lambda: mock_db
    try:
        resp = client.patch(
            "/session-drinks/drink-1/verdict",
            json={"verdict": "liked"},
            headers=AUTH_HEADER,
        )
    finally:
        app.dependency_overrides.clear()

    assert resp.status_code == 200
    assert resp.json() == DRINK_ROW
    mock_db.upsert_companion_like.assert_called_once_with("c-foreign", "bourbon")
