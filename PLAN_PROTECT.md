# PLAN_PROTECT — Fix what undermines the project's existing claims

**Goal:** Close the findings from `CodeReview.md` that make the resume story *untrue* or make its headline metrics *wrong*. This plan must be fully complete before `PLAN_EXTEND.md` begins — the extend work produces new metric tables, and every number it generates is unreliable until the matcher bugs, the mislabeled mock, and the self-judging bias here are fixed.

**Kill switch / ordering rule:** If any subtask in this plan is unfinished, do not start `PLAN_EXTEND.md`. Extend is blocked on `PLAN_PROTECT` 100% complete.

**Environment:**
- Python 3.14, venv at `.venv`.
- Tests: `.venv/bin/python -m pytest -q`
- Evals (offline/mock): `.venv/bin/python -m evals.run_evals`
- Evals (live): `.venv/bin/python -m evals.run_evals --live --judge` (needs `ANTHROPIC_API_KEY`)
- Git binary: `/opt/homebrew/bin/git` (shell `git` wrapper is broken here)
- Supabase migrations applied via `supabase db push` (human step)
- Co-author trailer required on commits. Never commit `.env`.

---

## Human-required steps

- **1.4** — Apply the new RPC-ownership migration to the live Supabase project via `supabase db push` (external service; agent has no dashboard/CLI auth).
- **1.5** — Provide/confirm `TEST_USER_A/B` credentials in `.env` so the live RLS RPC tests can run (private credentials; auto-skip otherwise).
- **3.5** — Run the live eval to capture real metric deltas after the matcher fix (spends API tokens; needs `ANTHROPIC_API_KEY`).
- **5.3** — Run live judge calibration after pinning the independent judge model (spends tokens; needs API key).
- **7.7** — Confirm the correct single canonical Railway URL to standardize on (only the user knows which deployment is current).

---

## Task 1 — H1: Cross-tenant preference writes via SECURITY DEFINER RPCs

**Produces:** A migration that makes `upsert_companion_like`/`upsert_companion_dislike` reject companions the caller doesn't own, plus tests proving the hole is closed. This is the single "do it now" security fix — currently any authenticated user can write preferences onto any companion UUID via PostgREST `/rpc`.

- [x] **1.1 Write migration `supabase/migrations/20260703000000_rpc_ownership_guard.sql`.**
      `CREATE OR REPLACE FUNCTION` for both `upsert_companion_like(p_companion_id uuid, p_value text)` and `upsert_companion_dislike(...)`. Keep `SECURITY DEFINER`. Add `SET search_path = ''` to each function. At the top of each function body, add:
      `IF NOT EXISTS (SELECT 1 FROM public.companions WHERE id = p_companion_id AND user_id = auth.uid()) THEN RAISE EXCEPTION 'not authorized for companion %', p_companion_id USING ERRCODE = '42501'; END IF;`
      Because `search_path` is now empty, fully-qualify every table reference (`public.companion_preferences`, `public.companions`). Preserve the existing `INSERT ... ON CONFLICT (companion_id, value) DO UPDATE SET type = ...` body after the guard. Do NOT change the grants (EXECUTE to `authenticated` stays).

- [x] **1.2 Mirror the guard into `supabase/migrations/20260622000000_init.sql`** so a fresh `db push` from scratch is also safe (the init file currently defines the unguarded versions). Update both function bodies there identically to 1.1. Leave the surrounding migration untouched.
      depends on: 1.1

- [x] **1.3 Add unit test `tests/test_rpc_guard.py`** (offline, mocked DB) asserting `backend/db.py`'s `upsert_companion_like`/`upsert_companion_dislike` still call `self._sb.rpc(...)` with the expected params. This locks the Python call contract so the extend/refactor work can't silently break it. (The ownership enforcement itself is DB-side and covered live in 1.5.)
      **Verify:** `.venv/bin/python -m pytest -q tests/test_rpc_guard.py` green.
      depends on: 1.1

- [ ] **1.4 Apply the migration to live Supabase.** Run `supabase db push`.
      Requires human: applying a migration to the hosted Supabase project needs dashboard/CLI credentials an agent doesn't have. Hand over the command and the migration path; wait for confirmation it applied cleanly.
      depends on: 1.2

- [ ] **1.5 Add live RLS test `test_rls_rpc_isolation` to `tests/test_rls_isolation.py`.**
      Using the existing two-user `_sign_in` fixture pattern: User A creates a companion; User B (via `DB(jwt_b).upsert_companion_like(companion_a_id, "bourbon")`) must fail (expect an exception / non-success). Then assert via User A that no preference row was created for that companion. Auto-skip when `TEST_USER_A/B` env vars are absent (reuse the existing `live_rls` skipif marker). Self-clean created rows in a `finally`.
      Requires human: running this test live needs the two test-user credentials in `.env`; without them it auto-skips. Confirm creds are present and run `.venv/bin/python -m pytest tests/test_rls_isolation.py -v`.
      depends on: 1.4

---

## Task 2 ✅ — H2: Companion-ownership guard in POST /recommend

**Produces:** `/recommend` rejects `companion_ids` that don't belong to the authenticated user with a 400 before any session is created — implementing the guard the backend spec declares mandatory but the code never had.

- [x] **2.1 Add `list_companion_ids()` helper to `backend/db.py`** — returns the set of the current user's companion IDs: `{r["id"] for r in self._sb.table("companions").select("id").execute().data}`. RLS already scopes this to the user. One method, no business logic.

- [x] **2.2 Add the ownership guard in `app/main.py` `recommend_drinks`.**
      After the inventory fetch and BEFORE `db.get_active_session()`/`create_session`: if `req.companion_ids` is non-empty, fetch `owned = db.list_companion_ids()`; if any requested ID is not in `owned`, `raise HTTPException(status_code=400, detail="One or more companion IDs are not yours")`. Remove the now-stale "Future: accept companion_ids; for now trust..." comment block.
      depends on: 2.1

- [x] **2.3 Add unit tests to `tests/test_recommend_endpoint.py`.**
      (a) `test_recommend_rejects_foreign_companion`: mock `list_companion_ids` to return `{"c1"}`, POST with `companion_ids=["c-foreign"]`, expect 400 and assert `create_session` was NOT called. (b) `test_recommend_accepts_owned_companion`: `list_companion_ids` returns `{"c1"}`, POST with `companion_ids=["c1"]`, expect 200. Extend the `_mocked` context manager to stub `list_companion_ids`.
      **Verify:** `.venv/bin/python -m pytest -q tests/test_recommend_endpoint.py` green.
      depends on: 2.2

---

## Task 3 — M2: Category-aware bottle matcher

**Produces:** `match_bottle` stops producing the two known errors that distort every grounding/makeable number: the false positive ("orange bitters" matching "Orange Curaçao" on the shared fruit word) and the false negative (generic "bourbon" never matching "Four Roses Small Batch" because category is never consulted). Metric deltas recorded in RESUME_STORY.

- [x] **3.1 Add a category-token fallback to `recommender/inventory_match.py`.**
      Introduce a `_CATEGORY_TERMS` mapping of generic spirit/category words → the `Bottle.category`/`subcategory` values they should match (e.g. `"bourbon" → {"bourbon"}`, `"rye" → {"rye"}`, `"mezcal" → {"mezcal"}`, `"tequila" → {"tequila"}`, `"gin" → {"gin"}`, `"rum" → {"rum"}`, `"vodka" → {"vodka"}`, `"campari" → subcategory "amaro"` only if you keep it name-based — prefer category where possible). In `match_bottle`, after the existing name-token overlap check finds nothing, if the ingredient's normalized tokens contain a category term, match any owned bottle whose `category` (or `subcategory`) equals that term. Keep the existing name-overlap path as the primary; the category path is a fallback only.

- [x] **3.2 Fix the false-positive path in `match_bottle`.**
      Ensure a bare fruit/qualifier token shared between an ingredient and an unrelated bottle can't alone produce a match. "orange bitters" (tokens after stopwords: `{orange}`) must NOT match "Orange Curaçao" (`{orange, curacao}` → but "orange" as a lone overlap on a liqueur is wrong). Decide the rule explicitly: a single generic fruit/adjective token (`orange`, `lemon`, `lime`, `dry`, `sweet`, `spiced`, `aged`, `white`, `blanco`) does not carry a match by itself unless it is the category term matched via 3.1. Add these to a `_WEAK_TOKENS` set checked in the scoring path.
      depends on: 3.1

- [x] **3.3 Add property tests `tests/test_inventory_match.py` (extend existing).**
      Assert, against the `evals.fixtures.INVENTORY`: (a) `match_bottle("orange bitters", INVENTORY)` is None (Angostura is `bitters`, Cointreau/Curaçao is `orange` — neither is orange bitters); (b) `match_bottle("bourbon", INVENTORY)` returns the Four Roses bottle (category fallback); (c) `match_bottle("rye", INVENTORY)` returns Rittenhouse (unchanged, must not regress); (d) `match_bottle("Peychaud's Bitters", INVENTORY)` is None (must not regress the stopword fix). 
      **Verify:** `.venv/bin/python -m pytest -q tests/test_inventory_match.py` green.
      depends on: 3.2

- [x] **3.4 Re-run the offline eval and confirm no property-assertion regressions.**
      `.venv/bin/python -m evals.run_evals --strict`. If the matcher change moves any scenario's grounding below its `expect_min_grounded_rate`, investigate whether that's a real fix or a matcher bug before proceeding. Record the new mock grounding/makeable numbers.
      **Verify:** exits 0.
      depends on: 3.3

- [ ] **3.5 Run the live eval and record metric deltas in `RESUME_STORY.md`.**
      `.venv/bin/python -m evals.run_evals --live --judge`. Add a short "matcher fix" entry to the metrics timeline showing before/after grounding + makeable, framed as "found two matcher bugs distorting the metric; fixed both; here's the corrected baseline."
      Requires human: this spends API tokens and needs `ANTHROPIC_API_KEY`; the user must approve/run the live call and eyeball the suggestions for sanity.
      depends on: 3.4

---

## Task 4 — M3: Fix the mislabeled mock and harden --strict

**Produces:** The `companion_bitter_only` mock stops seeding a hidden violation while claiming to be "clean," and `--strict` actually guards the scenarios whose mocks are meant to be fully grounded.

- [x] **4.1 Fix the `companion_bitter_only` mock in `evals/mock_responses.py`.**
      The Campari Spritz uses `soda water` tagged `source: pantry`, which isn't in the allowlist, so it registers as a violation despite the "clean" annotation. Change `soda water` to `source: "perishable"` (it varies household to household — correct classification) so the mock is genuinely clean. Keep the annotation comment accurate.

- [x] **4.2 Add `expect_min_grounded_rate=1.0` to the clean scenarios in `evals/fixtures.py`** that currently lack it but whose mocks are meant to be fully grounded: `companion_mezcal` is a *seeded-violation* scenario (leave it), but `companion_smoke_sweet` and `companion_bitter_only` are clean — add the assertion to those two so `--strict` protects them. Do NOT add it to the adversarial/seeded scenarios (tiki, margarita, negroni_no_gin, etc.).
      depends on: 4.1

- [x] **4.3 Refresh the documented mock baseline.**
      Run `.venv/bin/python -m evals.run_evals --strict`, capture the new mock grounding rate (was quoted as 53%/12 scenarios; actual is 55%/14). Update the number and scenario count everywhere it appears in `RESUME_STORY.md` and `README.md`.
      **Verify:** exits 0; grep confirms no remaining "53%" / "12 scenario" references tied to the mock baseline.
      depends on: 4.2

---

## Task 5 — M4: Independent (pinned) judge model

**Produces:** The LLM judge always runs on one fixed model regardless of the candidate model being evaluated, removing self-preference bias from `run_evals` and making `sweep` judge columns comparable across rows.

- [x] **5.1 Add a fixed judge model constant + wiring in `evals/run_evals.py`.**
      Introduce `JUDGE_MODEL = "claude-haiku-4-5-20251001"` (or a `--judge-model` arg defaulting to it). In the `--judge` branch, build a *separate* `AnthropicClient(model=JUDGE_MODEL)` for judging instead of reusing the candidate `llm`. The recommend call keeps using the candidate model; only judging is pinned.

- [x] **5.2 Do the same in `evals/sweep.py`.**
      `run_model` currently builds `judge_llm = AnthropicClient(model=model_id)` — change it to the pinned `JUDGE_MODEL` so judge scores are identical-basis across swept models. Add a note in the printed output/header that the judge is pinned.
      depends on: 5.1

- [ ] **5.3 Re-run judge calibration and re-record agreement.**
      With the pinned judge, run the calibration flow (`scripts/full_eval.sh` then rename `judge_verdicts.json` → `judge_verdicts_calibration.json`, then `.venv/bin/python -m evals.calibrate_judge`). Update the P2 calibration numbers in `RESUME_STORY.md` if they moved, and note the judge is now model-pinned.
      Requires human: spends API tokens, needs `ANTHROPIC_API_KEY`, and calibration involves eyeballing agreement/disagreements.
      depends on: 5.2

---

## Task 6 — M5: Return drink IDs from /recommend

**Produces:** The frontend stops guessing which drink card maps to which DB row by list position (fragile under identical batch timestamps) — the API returns the IDs directly.

- [x] **6.1 Return created drink IDs from `app/main.py` `recommend_drinks`.**
      `db.create_session_drinks(session_id, drinks_payload)` already returns the inserted rows. Capture them and include their IDs in the response body — add a `drink_ids: list[str]` field to the JSON response (aligned by index with `result.suggestions`), alongside the existing `suggestions`. Keep the `X-Session-Id` header. Ensure `create_session_drinks` insert order matches suggestion order.

- [x] **6.2 Update `tests/test_recommend_endpoint.py`.**
      Extend `test_recommend_saves_drinks_to_session` (or add a new test) to assert the response body contains `drink_ids` with one ID per suggestion, matching the IDs returned by the mocked `create_session_drinks`. Update the mock's `create_session_drinks.return_value` to include `id` fields.
      **Verify:** `.venv/bin/python -m pytest -q tests/test_recommend_endpoint.py` green.
      depends on: 6.1

- [x] **6.3 Consume `drink_ids` in `app/static/index.html`.**
      In the `/recommend` submit handler, replace the positional inference (`sessionDrinks[priorDrinks.length + i]?.id`) for the *new batch* with the `drink_ids` array from the response. Prior batches still come from the `GET /sessions/{id}/drinks` fetch (those already carry stable IDs). Verify verdict buttons on the new batch carry the correct `data-drink-id`.
      depends on: 6.1

---

## Task 7 — Doc-truth batch

**Produces:** Documentation stops contradicting the code. Small, mechanical, high-trust-per-minute fixes. (Number-refresh items that depend on eval re-runs are handled in Tasks 3–5; this task is the remaining textual/structural cleanup.)

- [x] **7.1 Fix the `backend/db.py` module docstring.**
      The usage example reads `db = DB(user_jwt=user_id_from_auth_dep)` — passing the user_id, the exact P6.9 bug. Change it to pass the raw Bearer JWT and make the surrounding comment unambiguous that `user_jwt` is the token, never the `sub`/user_id.

- [x] **7.2 Reconcile "12 vs 14 scenarios" across docs.**
      Grep `README.md`, `RESUME_STORY.md`, `docs/eval-spec.md` for "12 scenario"/"14 scenario" and standardize on the actual count (14). Where a historical milestone genuinely used a smaller set, label it explicitly as "(historical, N-scenario set)" rather than leaving a bare inconsistent number.

- [x] **7.3 Refresh README token/cost figures from trace data.**
      README claims ~600 input tokens/request; trace data averages ~1,320. Update the per-request token and cost figures in `README.md`'s Cost section to match the recorded trace numbers (cite the trace summary in RESUME_STORY as the source).

- [x] **7.4 State explicitly that RAG is eval-only.**
      In `README.md` and `RESUME_STORY.md`, add one sentence where RAG is discussed: production `/recommend` does not use retrieval (`use_retrieval=False`); RAG exists behind the eval `--rag` flag, and the A/B showed it trailing on constraints — so it was deliberately not shipped. Removes the impression that RAG is in the live product.

- [x] **7.5 Delete the duplicate migration `backend/migrations/001_init.sql`.**
      It is a near-identical copy of `supabase/migrations/20260622000000_init.sql` (grants inline vs separate file) — two schema sources of truth. Remove `backend/migrations/001_init.sql` (and the now-empty `backend/migrations/` dir if nothing else lives there). Update any README/PLAN reference that points at it to point at `supabase/migrations/`.

- [x] **7.6 Delete `.env.copy`.**
      It holds real secrets on disk (untracked). Remove it; if a template is wanted, `env.template` already exists with placeholders. Confirm `git ls-files` shows it was never tracked before deleting.

- [ ] **7.7 Standardize on one Railway URL.**
      PLAN.md history shows `drinksuggesterproject-production...`; README/RESUME_STORY show `barback-production...`. Replace stale occurrences with the single canonical live URL across `README.md` and `RESUME_STORY.md`.
      Requires human: only the user knows which Railway deployment is the current/canonical one — confirm the URL before mass-replacing.

- [x] **7.8 (Optional, low-risk) Rename `SUPABASE_JWT_TOKEN` → `SUPABASE_JWT_SECRET`.**
      It holds the JWT signing *secret*, not a token. Update `backend/auth.py`, `env.template`, `README.md`, and `tests/test_rls_isolation.py`'s `_REQUIRED` list consistently. If the live deploy's env var can't be renamed easily, skip this and instead add a clarifying comment at each use site.
      Requires human: renaming the env var in the Railway/Supabase deploy dashboards is an external action; if not renaming there, leave the code var name and add comments only.

---

## Execution Rules

- After each subtask completes: commit with a descriptive message (co-author trailer; absolute git binary `/opt/homebrew/bin/git`).
- A subtask tagged `Requires human:` is a hard stop — present what's needed to the user and wait; never fabricate the input or stub past it.
- After each full Task completes:
  1. Run all tests (`.venv/bin/python -m pytest -q`)
  2. Confirm coverage > 80% on changed modules
  3. Spawn a sub-agent to review: verify task complete, all subtasks done, no regressions
  4. If tests fail or coverage < 80%: fix, re-run, commit fixes — loop until passing
- Mark done in this file: `- [ ]` → `- [x]` after each subtask and task.
- **Do not begin `PLAN_EXTEND.md` until every box in this file is `[x]`.**
