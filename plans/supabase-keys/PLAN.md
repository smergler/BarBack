# PLAN_SUPABASE_KEYS — Move to publishable/secret API keys, drop the HS256 JWT secret

Supabase is deprecating the JWT-based `anon` and `service_role` API keys in favor of
`sb_publishable_…` and `sb_secret_…` keys. This plan makes BarBack **require** the new keys
(legacy keys are rejected with an explicit error, not silently accepted). It also removes the
legacy HS256 JWT-secret verification path, so user tokens are verified only through the
project's asymmetric JWKS.

## Decisions (made up front, do not re-litigate during build)

| Old | New | Used by |
|---|---|---|
| `SUPABASE_ANON_KEY` | `SUPABASE_PUBLISHABLE_KEY` (must start `sb_publishable_`) | `backend/db.py`, `/config` → browser, RLS tests |
| `SUPABASE_PRIVATE_KEY` (service_role) | `SUPABASE_SECRET_KEY` (must start `sb_secret_`) | `scripts/create_test_users.py` only |
| `SUPABASE_JWT_TOKEN` (HS256 secret) | **removed** | was used by `backend/auth.py` HS256 branch |
| `/config` field `supabase_anon_key` | `supabase_publishable_key` | `app/static/index.html` |

- **Hard cutover, no fallback.** If a new var is missing or has the wrong prefix, raise `SupabaseKeyError`. If the value starts with `eyJ`, the error says it is a legacy JWT key. If the old var is set and the new one is not, the error names the new var to set.
- **Error messages never include the key value**, not even a prefix. They name only the env var.
- **Request path:** `SupabaseKeyError` maps to HTTP 503 `"Supabase not configured: <message>"` through a FastAPI exception handler. Keys are **not** validated at app startup. Unit tests import `app.main` without Supabase env, and a startup check would break them.
- **Auth:** `get_current_user` accepts only asymmetric algorithms (`ES256`, `RS256` and the rest of the existing `_ASYMMETRIC` set). An `HS256` token gets a 401 `Unsupported token algorithm`. Any HS256 token issued before cutover therefore gets a 401, and that user has to sign in again. This is intended.
- **Dependencies:** `supabase>=2.31,<3.0`. 2.31 is the installed version and is confirmed to have no JWT-format check on the key. Also `PyJWT[crypto]>=2.8,<3.0`. The JWKS path needs `cryptography`, which today arrives only as a transitive dependency.
- **The venv's `pip` shim is broken** (its shebang points at `drink_suggester_project`). Always run `.venv/bin/python -m pip …` and `.venv/bin/python -m pytest …`.
- **Historical docs are not edited:** `plans/` (all plan files, build logs and progress logs), `CodeReview.md`, `POSTMORTEM_*.md`. They record what was true at the time.

## Human-required steps

- **6.1** Confirm in the Supabase dashboard that the project signs JWTs with an asymmetric key (ES256/RS256), and migrate if it does not. Without this, removing HS256 breaks every login.
- **6.2** Create the publishable and secret keys in the Supabase dashboard.
- **6.3** Put the new keys in local `.env` and delete the three legacy vars.
- **6.4** Run the live RLS tests and `create_test_users.py` against the real project with the new keys.
- **6.5** Update the GitHub Actions secrets: add `SUPABASE_PUBLISHABLE_KEY`, delete `SUPABASE_ANON_KEY` and `SUPABASE_JWT_TOKEN`.
- **6.6** Add `SUPABASE_PUBLISHABLE_KEY` to the Railway env vars **before** merging.
- **6.7** Merge to main (this triggers the Railway deploy), then smoke-test login and one data read in the browser.
- **6.8** Delete the legacy vars from Railway, then disable the legacy API keys and revoke the legacy JWT secret in the Supabase dashboard.

---

## Task 1 — Key loader module

Adds one place that reads and validates the new keys, so every caller fails the same way with the same clear error.

- [ ] 1.1 Create `backend/supabase_keys.py` with:
  - `class SupabaseKeyError(RuntimeError)`
  - constants `PUBLISHABLE_ENV = "SUPABASE_PUBLISHABLE_KEY"`, `SECRET_ENV = "SUPABASE_SECRET_KEY"`, `PUBLISHABLE_PREFIX = "sb_publishable_"`, `SECRET_PREFIX = "sb_secret_"`
  - private `_LEGACY = {PUBLISHABLE_ENV: "SUPABASE_ANON_KEY", SECRET_ENV: "SUPABASE_PRIVATE_KEY"}`
  - private `_load(env_name: str, prefix: str) -> str`. It reads `os.environ.get(env_name, "").strip()` and applies these rules in order:
    - (a) the value is empty and the legacy var is set: raise `"{env_name} is not set; {legacy} is deprecated — create a {prefix}… key in the Supabase dashboard and set {env_name}"`
    - (b) the value is empty: raise `"{env_name} is not set"`
    - (c) the value starts with `"eyJ"`: raise `"{env_name} holds a legacy JWT-format key; use a {prefix}… key"`
    - (d) the value does not start with `prefix`, or `len(value) == len(prefix)`: raise `"{env_name} must start with {prefix}"`
    - Otherwise return the value. No message may contain the value.
  - public `publishable_key() -> str` returns `_load(PUBLISHABLE_ENV, PUBLISHABLE_PREFIX)`. Public `secret_key() -> str` returns `_load(SECRET_ENV, SECRET_PREFIX)`.
  - `project_url() -> str` reads `SUPABASE_PROJECT_URL` and raises `SupabaseKeyError("SUPABASE_PROJECT_URL is not set")` if it is empty.
- [ ] 1.2 Write `tests/test_supabase_keys.py` using `monkeypatch`, with one test per case:
  - valid publishable key returns it
  - valid secret key returns it
  - missing key raises
  - missing key with the legacy var set gives a message that names the legacy var
  - an `eyJ…` value gives a message containing `"legacy JWT"`
  - a wrong prefix raises, and so does a bare prefix
  - a secret value passed as the publishable key raises, and the reverse also raises
  - surrounding whitespace is stripped
  - for every raising case, assert the env value is **not** a substring of `str(exc)`
  - `project_url` raises when it is unset

  depends on: 1.1

## Task 2 — Publishable key in the app (backend + browser)

Switches the per-request RLS client and the browser client to the publishable key.

depends on: Task 1 complete

- [ ] 2.1 In `backend/db.py` `_make_client`: replace the `os.environ[...]` reads with `project_url()` and `publishable_key()` from `backend.supabase_keys`, and rename the local `anon_key` to `key`. In the module docstring, change "Do NOT use the service key" to "Do NOT use the secret key (sb_secret_…)".
- [ ] 2.2 In `app/main.py`: import `SupabaseKeyError`, then register `@app.exception_handler(SupabaseKeyError)` returning `JSONResponse(status_code=503, content={"detail": f"Supabase not configured: {exc}"})`. Put it next to the existing `RecommendationError` handler.
  depends on: 2.1
- [ ] 2.3 In `app/main.py` `get_config()`: return `{"supabase_url": project_url(), "supabase_publishable_key": publishable_key()}`. Update the docstring to "safe — publishable key only". Remove the `supabase_anon_key` field. With the 2.2 handler in place, a missing key now gives a 503 instead of an empty string.
  depends on: 2.2
- [ ] 2.4 In `app/static/index.html` line ~240: change `cfg.supabase_anon_key` to `cfg.supabase_publishable_key`. Before `createClient`, add `if (!cfg.supabase_url || !cfg.supabase_publishable_key) throw new Error(cfg.detail || 'Supabase config missing');` so a 503 body reaches the existing `auth-error` display.
  depends on: 2.3
- [ ] 2.5 Write `tests/test_config_endpoint.py` with `TestClient(app)`:
  - valid env gives 200 with exactly the keys `supabase_url` and `supabase_publishable_key`, and `supabase_anon_key` absent
  - a missing publishable key gives 503 with `"SUPABASE_PUBLISHABLE_KEY"` in the detail
  - an `eyJ` key gives 503
  - with `SUPABASE_SECRET_KEY` set in env, the response body does not contain the secret value

  depends on: 2.3
- [ ] 2.6 Write `tests/test_db_client.py`. Monkeypatch `backend.db.create_client` with a `MagicMock` and assert:
  - `DB("user-jwt")` calls `create_client(<url>, <sb_publishable_ value>)` and then `.postgrest.auth("user-jwt")`
  - with the publishable key unset, `DB("x")` raises `SupabaseKeyError` and `create_client` is never called

  depends on: 2.1

## Task 3 — Secret key in the admin script

The only service-level caller is moving to `sb_secret_`.

depends on: Task 1 complete

- [ ] 3.1 In `scripts/create_test_users.py`, change `ENV_PATH` to `Path(os.environ.get("BARBACK_ENV_PATH", Path(__file__).parent.parent / ".env"))` so tests can point it away from the real `.env`. Then replace the `url`/`service_key` env reads and the `SystemExit` check with:
  ```python
  try:
      url, key = project_url(), secret_key()
  except SupabaseKeyError as e:
      raise SystemExit(str(e))
  ```
  Import both from `backend.supabase_keys`. To make that import work, add `sys.path.insert(0, str(Path(__file__).parent.parent))` before the import. Rename `service_key` to `key`, and change the docstring to "Requires SUPABASE_PROJECT_URL and SUPABASE_SECRET_KEY (sb_secret_…) in .env."
- [ ] 3.2 Write `tests/test_create_test_users_script.py`. It runs the script with `subprocess.run([sys.executable, "scripts/create_test_users.py"], env=…)`, with `SUPABASE_SECRET_KEY` unset and `SUPABASE_PRIVATE_KEY="eyJx"` set. It also sets `BARBACK_ENV_PATH` to a non-existent file under `tmp_path`, so the real `.env` is never read. It asserts a non-zero exit and `"SUPABASE_SECRET_KEY"` in stderr. The script exits before `create_client`, so no network call is made.

  depends on: 3.1

## Task 4 — Remove HS256 verification

User JWTs are verified only through the project JWKS, and the legacy JWT secret drops out of the codebase.

- [ ] 4.1 In `backend/auth.py`:
  - delete the whole `elif alg == "HS256":` branch
  - drop "HS256" and `SUPABASE_JWT_TOKEN` from the module docstring and replace them with: "Tokens are verified against the project's JWKS (asymmetric keys only). HS256 / the legacy JWT secret is not accepted."
  - move `_ASYMMETRIC` to module level as a `frozenset`
  - fix the `get_current_user` docstring and drop "HS256 (shared secret)"
  - leave the asymmetric branch logic unchanged
- [ ] 4.2 Rewrite `tests/test_auth.py` for asymmetric tokens:
  - at module level, generate an EC P-256 key with `cryptography` (`ec.generate_private_key(ec.SECP256R1())`)
  - `_make_token(...)` signs with `algorithm="ES256"` and the header `kid="test-kid"`
  - a fixture monkeypatches `backend.auth._get_jwks_client` to return a stub whose `get_signing_key_from_jwt(token)` returns `SimpleNamespace(key=<public key>)`, and sets `SUPABASE_PROJECT_URL`

  Keep these existing cases, ported:
  - valid token returns the user id
  - expired token → 401 "expired"
  - token signed by a *different* EC key → 401
  - wrong audience → 401
  - `service_role` role → 401 "role"
  - missing sub → 401
  - wrong issuer → 401
  - missing `SUPABASE_PROJECT_URL` → 503

  Add these:
  - an HS256-signed token → 401 with `"Unsupported token algorithm"`
  - an `alg: none` token → 401
  - an RS256 token (RSA 2048 key) verifies
  - the stub raising `jwt.exceptions.PyJWKClientError` → 503

  Make sure no test sets `SUPABASE_JWT_TOKEN`.

  depends on: 4.1

## Task 5 — Live tests, CI, dependencies, docs

Brings everything outside `backend/` and `app/` in line with the new variable names.

depends on: Task 2 complete, Task 3 complete, Task 4 complete

- [ ] 5.1 In `tests/test_rls_isolation.py`:
  - in `_REQUIRED`, replace `"SUPABASE_ANON_KEY", "SUPABASE_JWT_TOKEN"` with `"SUPABASE_PUBLISHABLE_KEY"`
  - in `_sign_in`, use `create_client(project_url(), publishable_key())` from `backend.supabase_keys`
  - update the skip reason string to mention `SUPABASE_PUBLISHABLE_KEY`
- [ ] 5.2 In the `Live RLS isolation` step env of `.github/workflows/ci.yml`:
  - replace `SUPABASE_ANON_KEY: ${{ secrets.SUPABASE_ANON_KEY }}` with `SUPABASE_PUBLISHABLE_KEY: ${{ secrets.SUPABASE_PUBLISHABLE_KEY }}`
  - delete the `SUPABASE_JWT_TOKEN` line
  - update the skip error message to name `SUPABASE_PUBLISHABLE_KEY`

  depends on: 5.1
- [ ] 5.3 In `requirements.txt`, change `supabase>=2.0,<3.0` to `supabase>=2.31,<3.0` and `PyJWT>=2.8,<3.0` to `PyJWT[crypto]>=2.8,<3.0`. Then run `.venv/bin/python -m pip install -r requirements.txt` to confirm it resolves.
- [ ] 5.4 Rewrite `env.template` lines 3–5 as `SUPABASE_PUBLISHABLE_KEY=sb_publishable_...` and `SUPABASE_SECRET_KEY=sb_secret_...   # only for scripts/create_test_users.py; never ship to the app`. Delete the `SUPABASE_JWT_TOKEN` line.
- [ ] 5.5 Update `README.md`:
  - env block (lines ~117–119): `SUPABASE_PUBLISHABLE_KEY=sb_publishable_...`, `SUPABASE_SECRET_KEY=sb_secret_...  # scripts only`, and remove `SUPABASE_JWT_TOKEN`
  - feature line ~164: "Supabase Auth (JWKS verification of asymmetric JWTs, aud/iss/role checks, service_role rejected; legacy anon/service_role/HS256 keys not supported)"
- [ ] 5.6 Add `tests/test_no_legacy_supabase_vars.py`. It runs `git grep -nE "SUPABASE_(ANON_KEY|PRIVATE_KEY|JWT_TOKEN)|supabase_anon_key"` via `subprocess` over tracked files. It excludes the `plans/` directory (via a `:(exclude)plans` pathspec), `CodeReview.md`, `POSTMORTEM_*.md`, `KNOWN_ISSUES.md` and this test file, plus `backend/supabase_keys.py`, which names the legacy vars in its migration messages. It asserts the output is empty. Skip if `git` is unavailable.
  depends on: 5.5
- [ ] 5.7 Add one entry to `KNOWN_ISSUES.md` under resolved items: "Migrated to Supabase publishable/secret API keys and JWKS-only verification. SUPABASE_JWT_TOKEN misnomer resolved by removal." Also delete the misnomer note if one exists there.

## Task 6 — Rollout (human-gated)

Gets the new keys into every environment in an order that never leaves production without a working key.

depends on: Task 5 complete

- [ ] 6.1 In Supabase Dashboard → Project Settings → JWT Keys, confirm the **current** signing key is ECC (ES256) or RSA. If it is still "Legacy HS256 shared secret", migrate the JWT secret, then rotate to the asymmetric key, and wait for existing tokens to expire (the default is 1h).
  Requires human: dashboard action on an external service; only the owner can see and change the project's signing keys
- [ ] 6.2 In Dashboard → Project Settings → API Keys, create a publishable key and a secret key (name the secret `barback-scripts`).
  Requires human: creating credentials on an external service; an agent must never generate or invent key values
  depends on: 6.1
- [ ] 6.3 In local `.env`, add `SUPABASE_PUBLISHABLE_KEY` and `SUPABASE_SECRET_KEY`, and delete `SUPABASE_ANON_KEY`, `SUPABASE_PRIVATE_KEY` and `SUPABASE_JWT_TOKEN`.
  Requires human: only the user holds the key values; they must not pass through the agent transcript
  depends on: 6.2
- [ ] 6.4 Run `.venv/bin/python -m pytest tests/test_rls_isolation.py -v` (all 4 must pass, none skipped), then `.venv/bin/python scripts/create_test_users.py` (it must print "skipping" or "Created", not an error).
  Requires human: hits the live Supabase project with real credentials
  depends on: 6.3
- [ ] 6.5 In GitHub → repo Settings → Secrets → Actions, add `SUPABASE_PUBLISHABLE_KEY`, then delete `SUPABASE_ANON_KEY` and `SUPABASE_JWT_TOKEN`. Push the branch and confirm the CI "Live RLS isolation" step passes.
  Requires human: modifying secrets on an external service
  depends on: 6.4
- [ ] 6.6 In Railway → service → Variables, add `SUPABASE_PUBLISHABLE_KEY`. Do not add `SUPABASE_SECRET_KEY`, because the app does not use it. Leave the old vars for now.
  Requires human: modifying a production environment
  depends on: 6.5
- [ ] 6.7 Merge to main, which makes Railway redeploy. In a browser on the production URL:
  - `/config` returns `supabase_publishable_key`
  - sign-in works
  - the inventory list loads
  - a request with an old HS256 token (if you have one) gets a 401

  Requires human: production deploy plus observed manual verification
  depends on: 6.6
- [ ] 6.8 Delete `SUPABASE_ANON_KEY` and `SUPABASE_JWT_TOKEN` from Railway. Then, in the Supabase dashboard, disable the legacy `anon`/`service_role` API keys and revoke the legacy HS256 JWT secret. Re-check production sign-in afterwards.
  Requires human: irreversible change to external services
  depends on: 6.7

**Kill switch:** if 6.7 sign-in fails with a 401 on fresh logins, the project is still issuing HS256 tokens and 6.1 was not actually done. Revert the merge (Railway redeploys the old code, and the old vars are still present because 6.8 hasn't run), then redo 6.1.

## Execution Rules

- After each subtask completes: commit with a descriptive message
- A subtask tagged `Requires human:` is a hard stop — present what's needed to the user and wait; never fabricate the input or stub past it
- After each full Task completes:
  1. Run all tests
  2. Confirm coverage > 80%
  3. Spawn a sub-agent to review: verify task complete, all subtasks done, no regressions
  4. If tests fail or coverage < 80%: fix, re-run, commit fixes — loop until passing
- Mark done in this file: `- [ ]` → `- [x]` after each subtask and task
