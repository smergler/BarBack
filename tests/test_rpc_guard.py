"""Unit tests for companion preference RPC call contract.

Verifies that DB.upsert_companion_like / upsert_companion_dislike call
self._sb.rpc(...) with the correct params. Ownership enforcement is DB-side
and covered in the live RLS test (test_rls_isolation.py).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from backend.db import DB


@pytest.fixture
def mock_db():
    with patch("backend.db._make_client") as mk:
        sb = MagicMock()
        mk.return_value = sb
        db = DB(user_jwt="fake-jwt")
        yield db, sb


def test_upsert_companion_like_calls_rpc(mock_db):
    db, sb = mock_db
    sb.rpc.return_value.execute.return_value = MagicMock()

    db.upsert_companion_like("comp-uuid-123", "bourbon")

    sb.rpc.assert_called_once_with(
        "upsert_companion_like",
        {"p_companion_id": "comp-uuid-123", "p_value": "bourbon"},
    )
    sb.rpc.return_value.execute.assert_called_once()


def test_upsert_companion_dislike_calls_rpc(mock_db):
    db, sb = mock_db
    sb.rpc.return_value.execute.return_value = MagicMock()

    db.upsert_companion_dislike("comp-uuid-456", "sweet")

    sb.rpc.assert_called_once_with(
        "upsert_companion_dislike",
        {"p_companion_id": "comp-uuid-456", "p_value": "sweet"},
    )
    sb.rpc.return_value.execute.assert_called_once()
