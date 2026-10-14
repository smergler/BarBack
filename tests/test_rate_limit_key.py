import jwt
from starlette.requests import Request

from app.main import _rate_limit_key


def _req(headers: dict[str, str], client=("100.64.0.2", 1234)) -> Request:
    return Request({
        "type": "http",
        "headers": [(k.lower().encode(), v.encode()) for k, v in headers.items()],
        "client": client,
    })


def test_key_is_jwt_sub_for_bearer_token():
    token = jwt.encode({"sub": "user-123"}, "any-secret", algorithm="HS256")
    assert _rate_limit_key(_req({"Authorization": f"Bearer {token}"})) == "user-123"


def test_same_user_gets_same_key_across_proxy_addresses():
    token = jwt.encode({"sub": "user-123"}, "any-secret", algorithm="HS256")
    h = {"Authorization": f"Bearer {token}"}
    assert _rate_limit_key(_req(h, ("100.64.0.2", 1))) == _rate_limit_key(_req(h, ("100.64.0.7", 1)))


def test_falls_back_to_remote_address_without_authorization():
    assert _rate_limit_key(_req({})) == "100.64.0.2"


def test_falls_back_on_malformed_token():
    assert _rate_limit_key(_req({"Authorization": "Bearer not-a-jwt"})) == "100.64.0.2"


def test_falls_back_when_token_has_no_sub():
    token = jwt.encode({"aud": "x"}, "any-secret", algorithm="HS256")
    assert _rate_limit_key(_req({"Authorization": f"Bearer {token}"})) == "100.64.0.2"
