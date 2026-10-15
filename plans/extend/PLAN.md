# PLAN_EXTEND — Extend the story

**Goal:** Add the high-resume-signal capabilities from `CodeReview.md` that build *new* narrative on top of a corrected foundation: complete the RAG story arc with ingredient-coverage retrieval, make every published number defensible with multi-run averaging, shrink the deploy footprint, and cut eval token cost as an engineering-signal exercise.

**BLOCKED ON:** `plans/protect/PLAN.md` and `plans/harden/PLAN.md` 100% complete. Every metric this plan produces (coverage-retrieval A/B, multi-run averages, token deltas) is only trustworthy after the matcher bugs, mislabeled mock, and self-judging bias are fixed. Do not start Task 1 here until all boxes in `plans/protect/PLAN.md` are `[x]`.

**Environment:**
- Python 3.14, venv at `.venv`.
- Tests: `.venv/bin/python -m pytest -q`
- Evals: `.venv/bin/python -m evals.run_evals` (`--rag`, `--live`, `--judge`, `--strict`, `--trace`)
- Git binary: `/opt/homebrew/bin/git`
- Co-author trailer required. Never commit `.env`.

---

## Human-required steps

- **1.6** — Run the live A/B eval (no-RAG vs semantic RAG vs coverage retrieval) to capture the comparison table (spends API tokens; needs `ANTHROPIC_API_KEY`; involves reading suggestions for sanity).
- **2.4** — Run the multi-run live eval to populate mean±spread headline numbers (spends tokens; needs API key).
- **3.5** — Verify the Railway deploy image actually shrinks after the requirements split (external deploy; only the user can trigger/observe the Railway build).
- **4.4** — Run the live judge to measure the token delta from batching + caching (spends tokens; needs API key).

---

## Task 1 — Ingredient-coverage retrieval (RAG story, third act)

**Produces:** A deterministic retrieval mode that finds recipes the user can *actually make* from owned bottles (set math over `data/cocktails.json`), plus an A/B eval against semantic RAG and no-RAG. This is the highest-signal item in the review: your own P3 conclusion said coverage retrieval "might be more appropriate than semantic retrieval" — this implements and measures that hypothesis.

- [ ] **1.1 Create `retrieval/coverage.py` with `coverage_search(inventory, k=5) -> list[Recipe]`.**
      Load `data/cocktails.json`. For each recipe, compute a coverage score = (# recipe ingredients that match an owned bottle via `recommender.inventory_match.match_bottle`, OR are pantry/perishable staples) / (total recipe ingredients). Return the top-k recipes by coverage score, descending. Reuse the `Recipe` dataclass from `retrieval/search.py` (import or mirror it). No embeddings, no torch — pure set math.
      depends on: PLAN_PROTECT complete

- [ ] **1.2 Add `tests/test_coverage.py`.**
      With a small fixture inventory (bourbon + Campari + sweet vermouth) and a tiny inline recipe list: assert a Boulevardier-shaped recipe (all owned) scores higher than a Mai Tai-shaped recipe (mostly unowned); assert `coverage_search` returns at most `k`; assert an empty inventory yields low/zero scores without crashing.
      **Verify:** `.venv/bin/python -m pytest -q tests/test_coverage.py` green.
      depends on: 1.1

- [ ] **1.3 Wire a retrieval-mode selector into `recommender/context.py`.**
      Generalize `build_context`'s `use_retrieval: bool` into `retrieval_mode: str = "none"` accepting `"none" | "semantic" | "coverage"` (keep `use_retrieval=True` as a backward-compatible alias mapping to `"semantic"` so existing callers/tests don't break). For `"coverage"`, call `coverage_search(inventory, k=5)` and format the results with the existing `_format_retrieved` (naming-reference framing, outside `<user_data>`).
      depends on: 1.1

- [ ] **1.4 Thread `retrieval_mode` through `recommender/recommender.py`.**
      `recommend(...)` gains `retrieval_mode: str = "none"` (keep `use_retrieval` alias). Pass it into `build_context`.
      depends on: 1.3

- [ ] **1.5 Add `--retrieval {none,semantic,coverage}` to `evals/run_evals.py`.**
      Replace/augment the existing `--rag` flag: keep `--rag` as an alias for `--retrieval semantic`. Pass the mode into `recommend`. Print the active retrieval mode in the mode header line.
      depends on: 1.4

- [ ] **1.6 Run the three-way live A/B and record the table in `RESUME_STORY.md`.**
      Run `--live --judge` three times: `--retrieval none`, `--retrieval semantic`, `--retrieval coverage`. Build a comparison table (grounding, makeable-now, constraints, plausibility, name accuracy) and write the "third act" of the RAG arc: identified semantic RAG's over-anchoring → hypothesized coverage retrieval → measured it. State the verdict the data supports.
      Requires human: three live runs spend API tokens, need `ANTHROPIC_API_KEY`, and the conclusion requires reading the suggestions, not just the scores.
      depends on: 1.5

---

## Task 2 — Multi-run eval averaging

**Produces:** `run_evals` can run each scenario N times and report mean ± spread per metric, so the headline numbers stop being single-run points on data you documented as having ±15pp noise.

- [ ] **2.1 Add `--runs N` (default 1) to `evals/run_evals.py`.**
      For each scenario, run the recommend (and judge, if enabled) N times, collecting per-run grounding/makeable/judge values. When N=1, behavior and output are identical to today (no regression).

- [ ] **2.2 Aggregate to mean ± spread.**
      For each metric, compute mean and a spread measure (min–max range or stdev) across the N runs. Print an augmented summary: `GROUNDING RATE: 96% (±4%, n=3 runs)`. Keep the per-scenario table showing run-1 (or a representative run) so output stays readable.
      depends on: 2.1

- [ ] **2.3 Add `tests/test_multirun.py` (offline).**
      With MockClient (deterministic responses), assert `--runs 3` produces the same mean as `--runs 1` and zero spread (mocks are deterministic), and that the aggregation code handles N=1 without a spread line or with a zero spread. Test the aggregation function directly rather than shelling out.
      **Verify:** `.venv/bin/python -m pytest -q tests/test_multirun.py` green.
      depends on: 2.2

- [ ] **2.4 Run a multi-run live eval and update headline numbers with error bars.**
      `.venv/bin/python -m evals.run_evals --live --judge --runs 3`. Update the metrics timeline in `RESUME_STORY.md` and `README.md` to show mean ± spread for the live numbers, and add a sentence: "single-run judge dims carry ~±15pp noise; reported numbers are 3-run means."
      Requires human: spends API tokens (3× a full judge run), needs `ANTHROPIC_API_KEY`.
      depends on: 2.3

---

## Task 3 — Split requirements (drop torch from the app image)

**Produces:** The production/app dependency set no longer drags in `sentence-transformers`/torch (~2GB) that `/recommend` never uses; eval/RAG deps move to a separate file. Biggest deploy/CI build-time win in the review.

- [ ] **3.1 Create `requirements.txt` (app-only) and `requirements-eval.txt` (eval/RAG).**
      App file keeps: `pydantic`, `anthropic`, `python-dotenv`, `fastapi`, `uvicorn[standard]`, `slowapi`, `supabase`, `PyJWT`, `httpx` (if used by app), and `numpy` ONLY if the app path imports it (verify — if numpy is only used by retrieval, move it). Eval file gets: `numpy`, `sentence-transformers`, `pytest`, plus `-r requirements.txt` at the top so `pip install -r requirements-eval.txt` gives the full dev env. Keep the exact pins as-is.

- [ ] **3.2 Verify the app imports cleanly without eval deps.**
      In a scratch venv (or by grep): confirm nothing under `app/`, `backend/`, or the non-retrieval parts of `recommender/` imports `sentence_transformers` or `torch`. `recommender/context.py`'s retrieval import is already guarded by try/except ImportError — confirm that guard means the app boots without eval deps installed. Document the check.
      depends on: 3.1

- [ ] **3.3 Update `.github/workflows/ci.yml`.**
      CI runs tests + offline eval, so it needs eval deps: change its install step to `pip install -r requirements-eval.txt`. (Offline eval with `--strict` doesn't use retrieval, but tests may import eval modules — install the full set to be safe.)
      depends on: 3.1

- [ ] **3.4 Update `.github/workflows/nightly-eval.yml`** to `pip install -r requirements-eval.txt` (it runs the live eval + judge).
      depends on: 3.1

- [ ] **3.5 Confirm Railway uses `requirements.txt` (app-only) and the image shrinks.**
      Railway's build installs `requirements.txt` by default — after the split that's the slim app set. Redeploy and confirm the build no longer pulls torch and the image/build time drops.
      Requires human: triggering and observing a Railway deploy is an external action only the user can do; report back whether the torch download disappeared from the build log.
      depends on: 3.2

---

## Task 4 — Judge batching + prompt caching (eval token efficiency)

**Produces:** Measured reduction in eval token spend — judge calls batched per-scenario instead of per-suggestion, and `cache_control` on the repeated system prompts — quantified with the existing tracing harness. Engineering-signal, not cost-driven (savings are ~$0.10/run).

- [ ] **4.1 Add a batched judge function to `evals/judge.py`.**
      `judge_suggestions(suggestions: list[Suggestion], request, llm) -> list[JudgeVerdict]` — one LLM call scoring all of a scenario's suggestions, returning a verdict per suggestion (prompt asks for a JSON array keyed by suggestion index/name). Keep the single-suggestion `judge_suggestion` for calibration/back-compat. Parse defensively; on array-length mismatch, fall back to per-suggestion calls.

- [ ] **4.2 Use the batched judge in `evals/run_evals.py`.**
      In the `--judge` branch, call `judge_suggestions` once per scenario instead of looping `judge_suggestion` per suggestion. Preserve the `TaggedVerdict` tagging (scenario_id, suggestion_name, hash) and tracing writes (one `judge` trace record per batched call).
      depends on: 4.1

- [ ] **4.3 Add `cache_control` to the system prompt in `recommender/llm.py`.**
      In `AnthropicClient.generate`/`generate_structured`, send the `system` field as a content block with `cache_control: {"type": "ephemeral"}` so the repeated system prompt across eval scenarios is cached. (Consult the `claude-api` skill for the exact block shape before coding.) Guard so a model/SDK that doesn't support it degrades gracefully.
      depends on: PLAN_PROTECT complete

- [ ] **4.4 Measure the token delta with the tracing harness.**
      Run `--live --judge --trace` before (git stash / prior commit) and after; run `.venv/bin/python -m evals.trace_summary` on each. Record input/output token totals before vs after in `RESUME_STORY.md`'s observability section, framed as "batched the judge and cached the system prompt; here's the measured token reduction."
      Requires human: spends API tokens, needs `ANTHROPIC_API_KEY`.
      depends on: 4.2

- [ ] **4.5 Add `tests/test_judge_batch.py` (offline).**
      With a MockClient returning a canned JSON array of verdicts, assert `judge_suggestions` parses N verdicts for N suggestions, and that a length-mismatch response triggers the per-suggestion fallback.
      **Verify:** `.venv/bin/python -m pytest -q tests/test_judge_batch.py` green.
      depends on: 4.1

---

## Task 5 — suited_for-aware verdict propagation

**Produces:** A drink's like/dislike only updates the preferences of companions it was actually targeted at (`suited_for`), instead of polluting every companion in the session.

- [ ] **5.1 Persist `suited_for` availability at verdict time (confirm the data path).**
      `session_drinks.suited_for` already exists (migration `20260625000000`) and is written by `create_session_drinks`. Confirm `db.get_session_drink`/`set_verdict` returns `suited_for` on the row so `_apply_feedback` can read it. If not selected, ensure the row fetch includes it.

- [ ] **5.2 Scope propagation to targeted companions in `backend/routers/session_drinks.py`.**
      In `_apply_feedback`, read `drink_row.get("suited_for", [])`. If non-empty, resolve those names to companion IDs (match against the session's companions by name) and apply preference upserts ONLY to those companions. If `suited_for` is empty (suits everyone) OR no name matches, keep the current behavior (apply to all session companions) as the sensible default.
      depends on: 5.1

- [ ] **5.3 Add tests to `tests/test_session_drinks.py`.**
      (a) A drink with `suited_for=["Alex"]` in a session with Alex + Sam updates only Alex's preferences; (b) a drink with empty `suited_for` updates all session companions (unchanged behavior); (c) `suited_for` naming a companion not in the session falls back gracefully (no crash). Mock the DB and assert the `upsert_*` calls target the right companion IDs.
      **Verify:** `.venv/bin/python -m pytest -q tests/test_session_drinks.py` green.
      depends on: 5.2

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
- **Precondition:** do not start this plan until every box in `plans/protect/PLAN.md` is `[x]`.
