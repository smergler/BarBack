"""Loads and validates Supabase API keys from the environment.

Only the new publishable/secret key formats are accepted. Legacy JWT-format
keys (anon / service_role) are rejected with an explicit error. Error messages
name the env var but never include the key value.
"""

from __future__ import annotations

import os

PUBLISHABLE_ENV = "SUPABASE_PUBLISHABLE_KEY"
SECRET_ENV = "SUPABASE_SECRET_KEY"
PUBLISHABLE_PREFIX = "sb_publishable_"
SECRET_PREFIX = "sb_secret_"

_LEGACY = {PUBLISHABLE_ENV: "SUPABASE_ANON_KEY", SECRET_ENV: "SUPABASE_PRIVATE_KEY"}


class SupabaseKeyError(RuntimeError):
    """A Supabase key or URL is missing or in the wrong format."""


def _load(env_name: str, prefix: str) -> str:
    value = os.environ.get(env_name, "").strip()
    if not value:
        legacy = _LEGACY[env_name]
        if os.environ.get(legacy):
            raise SupabaseKeyError(
                f"{env_name} is not set; {legacy} is deprecated — "
                f"create a {prefix}… key in the Supabase dashboard and set {env_name}"
            )
        raise SupabaseKeyError(f"{env_name} is not set")
    if value.startswith("eyJ"):
        raise SupabaseKeyError(f"{env_name} holds a legacy JWT-format key; use a {prefix}… key")
    if not value.startswith(prefix) or len(value) == len(prefix):
        raise SupabaseKeyError(f"{env_name} must start with {prefix}")
    return value


def publishable_key() -> str:
    return _load(PUBLISHABLE_ENV, PUBLISHABLE_PREFIX)


def secret_key() -> str:
    return _load(SECRET_ENV, SECRET_PREFIX)


def project_url() -> str:
    url = os.environ.get("SUPABASE_PROJECT_URL", "").strip()
    if not url:
        raise SupabaseKeyError("SUPABASE_PROJECT_URL is not set")
    return url
