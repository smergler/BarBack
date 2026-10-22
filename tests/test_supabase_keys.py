import pytest

from backend.supabase_keys import (
    PUBLISHABLE_ENV,
    SECRET_ENV,
    SupabaseKeyError,
    project_url,
    publishable_key,
    secret_key,
)

PUB = "sb_publishable_abc123"
SEC = "sb_secret_xyz789"


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (PUBLISHABLE_ENV, SECRET_ENV, "SUPABASE_ANON_KEY", "SUPABASE_PRIVATE_KEY", "SUPABASE_PROJECT_URL"):
        monkeypatch.delenv(name, raising=False)


def test_valid_publishable(monkeypatch):
    monkeypatch.setenv(PUBLISHABLE_ENV, PUB)
    assert publishable_key() == PUB


def test_valid_secret(monkeypatch):
    monkeypatch.setenv(SECRET_ENV, SEC)
    assert secret_key() == SEC


def test_missing_raises():
    with pytest.raises(SupabaseKeyError, match=PUBLISHABLE_ENV):
        publishable_key()
    with pytest.raises(SupabaseKeyError, match=SECRET_ENV):
        secret_key()


def test_missing_with_legacy_names_legacy_var(monkeypatch):
    monkeypatch.setenv("SUPABASE_ANON_KEY", "eyJlegacy")
    with pytest.raises(SupabaseKeyError) as ei:
        publishable_key()
    assert "SUPABASE_ANON_KEY" in str(ei.value)
    assert PUBLISHABLE_ENV in str(ei.value)
    assert "eyJlegacy" not in str(ei.value)
    monkeypatch.setenv("SUPABASE_PRIVATE_KEY", "eyJlegacy")
    with pytest.raises(SupabaseKeyError, match="SUPABASE_PRIVATE_KEY") as ei:
        secret_key()
    assert "eyJlegacy" not in str(ei.value)


def test_jwt_format_rejected(monkeypatch):
    monkeypatch.setenv(PUBLISHABLE_ENV, "eyJhbGciOi.payload.sig")
    with pytest.raises(SupabaseKeyError, match="legacy JWT"):
        publishable_key()


@pytest.mark.parametrize("value", ["wrong_prefix_123", "sb_publishable_"])
def test_wrong_prefix_or_bare_prefix(monkeypatch, value):
    monkeypatch.setenv(PUBLISHABLE_ENV, value)
    with pytest.raises(SupabaseKeyError, match="must start with"):
        publishable_key()


def test_secret_as_publishable_and_reverse(monkeypatch):
    monkeypatch.setenv(PUBLISHABLE_ENV, SEC)
    with pytest.raises(SupabaseKeyError):
        publishable_key()
    monkeypatch.setenv(SECRET_ENV, PUB)
    with pytest.raises(SupabaseKeyError):
        secret_key()


def test_whitespace_stripped(monkeypatch):
    monkeypatch.setenv(PUBLISHABLE_ENV, f"  {PUB}\n")
    assert publishable_key() == PUB


@pytest.mark.parametrize(
    "env,value,fn",
    [
        (PUBLISHABLE_ENV, "eyJsecretvalue", publishable_key),
        (PUBLISHABLE_ENV, "bogus_value_123", publishable_key),
        (SECRET_ENV, "sb_publishable_leakcheck", secret_key),
        (SECRET_ENV, "bogus_value_123", secret_key),
        (PUBLISHABLE_ENV, "sb_secret_leakcheck", publishable_key),
        (SECRET_ENV, "eyJsecretvalue", secret_key),
    ],
)
def test_error_never_contains_value(monkeypatch, env, value, fn):
    monkeypatch.setenv(env, value)
    with pytest.raises(SupabaseKeyError) as ei:
        fn()
    assert value not in str(ei.value)


def test_project_url_unset_raises():
    with pytest.raises(SupabaseKeyError, match="SUPABASE_PROJECT_URL"):
        project_url()


def test_project_url_set(monkeypatch):
    monkeypatch.setenv("SUPABASE_PROJECT_URL", "https://x.supabase.co")
    assert project_url() == "https://x.supabase.co"
