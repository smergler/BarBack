"""Tests for companions + preferences endpoints. DB is mocked."""

from __future__ import annotations

import contextlib
from unittest.mock import MagicMock

from fastapi import FastAPI
from fastapi.testclient import TestClient

from backend.routers.companions import _db, router

app = FastAPI()
app.include_router(router)
client = TestClient(app, raise_server_exceptions=False)

AUTH_HEADER = {"Authorization": "Bearer fake-jwt"}

COMPANION = {
    "id": "c1",
    "name": "wife",
    "created_at": "2026-01-01T00:00:00+00:00",
    "updated_at": "2026-01-01T00:00:00+00:00",
}
PREF = {
    "id": "p1",
    "companion_id": "c1",
    "type": "like",
    "value": "bourbon",
    "created_at": "2026-01-01T00:00:00+00:00",
}


def _mock_db(return_list=None, return_one=None, create_return=None, pref_list=None, pref_return=None):
    db = MagicMock()
    db.list_companions.return_value = return_list or []
    db.get_companion.return_value = return_one
    db.create_companion.return_value = create_return or COMPANION
    db.update_companion.return_value = return_one
    db.delete_companion.return_value = bool(return_one)
    db.list_preferences.return_value = pref_list or []
    db.create_preference.return_value = pref_return or PREF
    db.delete_preference.return_value = bool(return_one)
    return db


@contextlib.contextmanager
def _db_override(db):
    app.dependency_overrides[_db] = lambda: db
    try:
        yield
    finally:
        app.dependency_overrides.clear()


def test_list_requires_auth():
    resp = client.get("/companions")
    assert resp.status_code in (401, 403)


def test_list_companions():
    db = _mock_db(return_list=[COMPANION])
    with _db_override(db):
        resp = client.get("/companions", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json() == [COMPANION]
    db.list_companions.assert_called_once_with(limit=20, offset=0)


def test_create_companion():
    db = _mock_db(create_return=COMPANION)
    with _db_override(db):
        resp = client.post("/companions", json={"name": "wife"}, headers=AUTH_HEADER)
    assert resp.status_code == 201
    assert resp.json()["name"] == "wife"


def test_create_companion_conflict():
    db = _mock_db()
    db.create_companion.side_effect = Exception("unique constraint violated")
    with _db_override(db):
        resp = client.post("/companions", json={"name": "wife"}, headers=AUTH_HEADER)
    assert resp.status_code == 409


def test_update_companion_success():
    updated = {**COMPANION, "name": "husband"}
    db = _mock_db(return_one=updated)
    with _db_override(db):
        resp = client.put("/companions/c1", json={"name": "husband"}, headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json()["name"] == "husband"


def test_update_companion_not_found():
    db = _mock_db(return_one=None)
    with _db_override(db):
        resp = client.put("/companions/bad-id", json={"name": "X"}, headers=AUTH_HEADER)
    assert resp.status_code == 404


def test_delete_companion_success():
    db = _mock_db(return_one=COMPANION)
    with _db_override(db):
        resp = client.delete("/companions/c1", headers=AUTH_HEADER)
    assert resp.status_code == 204


def test_delete_companion_not_found():
    db = _mock_db(return_one=None)
    with _db_override(db):
        resp = client.delete("/companions/bad-id", headers=AUTH_HEADER)
    assert resp.status_code == 404


def test_list_preferences():
    db = _mock_db(pref_list=[PREF])
    with _db_override(db):
        resp = client.get("/companions/c1/preferences", headers=AUTH_HEADER)
    assert resp.status_code == 200
    assert resp.json() == [PREF]
    db.list_preferences.assert_called_once_with("c1")


def test_create_preference():
    db = _mock_db(pref_return=PREF)
    with _db_override(db):
        resp = client.post("/companions/c1/preferences",
                           json={"type": "like", "value": "bourbon"},
                           headers=AUTH_HEADER)
    assert resp.status_code == 201
    assert resp.json()["type"] == "like"


def test_create_preference_conflict():
    db = _mock_db()
    db.create_preference.side_effect = Exception("unique constraint violated")
    with _db_override(db):
        resp = client.post("/companions/c1/preferences",
                           json={"type": "like", "value": "bourbon"},
                           headers=AUTH_HEADER)
    assert resp.status_code == 409


def test_delete_preference_success():
    db = _mock_db(return_one=PREF)
    with _db_override(db):
        resp = client.delete("/companions/c1/preferences/p1", headers=AUTH_HEADER)
    assert resp.status_code == 204
    db.delete_preference.assert_called_once_with("p1")


def test_delete_preference_not_found():
    db = _mock_db(return_one=None)
    with _db_override(db):
        resp = client.delete("/companions/c1/preferences/bad-id", headers=AUTH_HEADER)
    assert resp.status_code == 404
