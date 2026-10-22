from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)
PUB = "sb_publishable_abc123"
SEC = "sb_secret_topsecretvalue"


def _env(monkeypatch, **kw):
    for name in ("SUPABASE_PROJECT_URL", "SUPABASE_PUBLISHABLE_KEY", "SUPABASE_SECRET_KEY",
                 "SUPABASE_ANON_KEY", "SUPABASE_PRIVATE_KEY"):
        monkeypatch.delenv(name, raising=False)
    for k, v in kw.items():
        monkeypatch.setenv(k, v)


def test_config_ok(monkeypatch):
    _env(monkeypatch, SUPABASE_PROJECT_URL="https://x.supabase.co", SUPABASE_PUBLISHABLE_KEY=PUB)
    r = client.get("/config")
    assert r.status_code == 200
    assert r.json() == {"supabase_url": "https://x.supabase.co", "supabase_publishable_key": PUB}
    assert "supabase_anon_key" not in r.json()


def test_config_missing_key_503(monkeypatch):
    _env(monkeypatch, SUPABASE_PROJECT_URL="https://x.supabase.co")
    r = client.get("/config")
    assert r.status_code == 503
    assert "SUPABASE_PUBLISHABLE_KEY" in r.json()["detail"]


def test_config_legacy_key_503(monkeypatch):
    _env(monkeypatch, SUPABASE_PROJECT_URL="https://x.supabase.co", SUPABASE_PUBLISHABLE_KEY="eyJlegacy.x.y")
    r = client.get("/config")
    assert r.status_code == 503
    assert "eyJlegacy" not in r.text


def test_config_never_leaks_secret(monkeypatch):
    _env(monkeypatch, SUPABASE_PROJECT_URL="https://x.supabase.co",
         SUPABASE_PUBLISHABLE_KEY=PUB, SUPABASE_SECRET_KEY=SEC)
    assert SEC not in client.get("/config").text
