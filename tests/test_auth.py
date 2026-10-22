"""Tests for the JWT auth dependency (asymmetric tokens verified via JWKS)."""

from __future__ import annotations

import time
from types import SimpleNamespace

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec, rsa
from fastapi import HTTPException
from fastapi.security import HTTPAuthorizationCredentials

import backend.auth as auth_mod
from backend.auth import get_current_user

TEST_USER_ID = "00000000-0000-0000-0000-000000000001"
TEST_PROJECT_URL = "https://test-project.supabase.co"
TEST_ISSUER = f"{TEST_PROJECT_URL}/auth/v1"

EC_KEY = ec.generate_private_key(ec.SECP256R1())
OTHER_EC_KEY = ec.generate_private_key(ec.SECP256R1())
RSA_KEY = rsa.generate_private_key(public_exponent=65537, key_size=2048)


def _make_token(
    key=EC_KEY,
    algorithm: str = "ES256",
    user_id: str | None = TEST_USER_ID,
    audience: str = "authenticated",
    role: str = "authenticated",
    exp_offset: int = 3600,
    issuer: str = TEST_ISSUER,
) -> str:
    payload = {
        "aud": audience,
        "role": role,
        "iss": issuer,
        "iat": int(time.time()),
        "exp": int(time.time()) + exp_offset,
    }
    if user_id is not None:
        payload["sub"] = user_id
    return jwt.encode(payload, key, algorithm=algorithm, headers={"kid": "test-kid"})


class _StubJwks:
    def __init__(self, public_key):
        self._public_key = public_key

    def get_signing_key_from_jwt(self, token):
        return SimpleNamespace(key=self._public_key)


@pytest.fixture(autouse=True)
def jwks(monkeypatch):
    monkeypatch.setenv("SUPABASE_PROJECT_URL", TEST_PROJECT_URL)
    monkeypatch.delenv("SUPABASE_JWT_TOKEN", raising=False)
    holder = {"key": EC_KEY.public_key()}
    monkeypatch.setattr(auth_mod, "_get_jwks_client", lambda: _StubJwks(holder["key"]))
    return holder


def _call(token: str) -> str:
    return get_current_user(HTTPAuthorizationCredentials(scheme="Bearer", credentials=token))


def _status(token: str) -> HTTPException:
    with pytest.raises(HTTPException) as exc:
        _call(token)
    return exc.value


def test_valid_token_returns_user_id():
    assert _call(_make_token()) == TEST_USER_ID


def test_expired_token_raises_401():
    e = _status(_make_token(exp_offset=-3600))
    assert e.status_code == 401
    assert "expired" in e.detail.lower()


def test_token_signed_by_different_key_raises_401():
    assert _status(_make_token(key=OTHER_EC_KEY)).status_code == 401


def test_wrong_audience_raises_401():
    assert _status(_make_token(audience="anon")).status_code == 401


def test_service_role_token_rejected():
    e = _status(_make_token(role="service_role"))
    assert e.status_code == 401
    assert "role" in e.detail.lower()


def test_missing_sub_raises_401():
    assert _status(_make_token(user_id=None)).status_code == 401


def test_wrong_issuer_raises_401():
    assert _status(_make_token(issuer="https://not-the-real-project.supabase.co/auth/v1")).status_code == 401


def test_missing_project_url_raises_503(monkeypatch):
    monkeypatch.delenv("SUPABASE_PROJECT_URL", raising=False)
    assert _status(_make_token()).status_code == 503


def test_hs256_token_rejected():
    token = jwt.encode(
        {"sub": TEST_USER_ID, "aud": "authenticated", "role": "authenticated", "iss": TEST_ISSUER,
         "iat": int(time.time()), "exp": int(time.time()) + 3600},
        "test-jwt-secret-32-chars-minimum!!",
        algorithm="HS256",
    )
    e = _status(token)
    assert e.status_code == 401
    assert "Unsupported token algorithm" in e.detail


def test_alg_none_rejected():
    token = jwt.encode({"sub": TEST_USER_ID}, key=None, algorithm="none")
    assert _status(token).status_code == 401


def test_rs256_token_verifies(jwks):
    jwks["key"] = RSA_KEY.public_key()
    assert _call(_make_token(key=RSA_KEY, algorithm="RS256")) == TEST_USER_ID


def test_jwks_client_error_raises_503(monkeypatch):
    class _Broken:
        def get_signing_key_from_jwt(self, token):
            raise jwt.exceptions.PyJWKClientError("jwks down")

    monkeypatch.setattr(auth_mod, "_get_jwks_client", lambda: _Broken())
    assert _status(_make_token()).status_code == 503


def test_malformed_token_raises_401():
    assert _status("not-a-jwt").status_code == 401
