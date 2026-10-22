from unittest.mock import MagicMock

import pytest

import backend.db as db_mod
from backend.supabase_keys import SupabaseKeyError

PUB = "sb_publishable_abc123"


def test_db_uses_publishable_key_and_user_jwt(monkeypatch):
    monkeypatch.setenv("SUPABASE_PROJECT_URL", "https://x.supabase.co")
    monkeypatch.setenv("SUPABASE_PUBLISHABLE_KEY", PUB)
    mock = MagicMock()
    monkeypatch.setattr(db_mod, "create_client", mock)
    db_mod.DB("user-jwt")
    mock.assert_called_once_with("https://x.supabase.co", PUB)
    mock.return_value.postgrest.auth.assert_called_once_with("user-jwt")


def test_db_missing_key_raises_without_client(monkeypatch):
    monkeypatch.setenv("SUPABASE_PROJECT_URL", "https://x.supabase.co")
    monkeypatch.delenv("SUPABASE_PUBLISHABLE_KEY", raising=False)
    monkeypatch.delenv("SUPABASE_ANON_KEY", raising=False)
    mock = MagicMock()
    monkeypatch.setattr(db_mod, "create_client", mock)
    with pytest.raises(SupabaseKeyError):
        db_mod.DB("x")
    mock.assert_not_called()
