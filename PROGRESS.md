# PROGRESS — PLAN_PROTECT.md

## 2026-07-03 — /build session (claude-sonnet-4-6)
- **Done:** 1.1, 1.2, 1.3, 2.1, 2.2, 2.3, 3.1, 3.2, 3.3, 3.4, 4.1, 4.2, 4.3, 5.1, 5.2, 6.1, 6.2, 6.3, 7.1, 7.2, 7.3, 7.4, 7.5, 7.6, 7.8
- **State:** 114 tests passing; offline eval exits 0 (--strict). Last green commit: b9fac62
- **Next:** Human-required items: 1.4 (supabase db push), 1.5 (live RLS test with TEST_USER creds), 3.5 (live eval run for matcher deltas), 5.3 (judge calibration re-run), 7.7 (confirm canonical Railway URL)
- **Broken/open:** BUILD_LOG has one [plan] entry — "dry"/"sweet" excluded from _WEAK_TOKENS to avoid breaking vermouth-matching tests; plan listed them but they're vermouth subcategory qualifiers. Reviewer should confirm this was the right call.

## 2026-10-13 — /build session (PLAN_HARDEN.md, claude-sonnet-5-5)
- **Done:** 7.1 (reverted guard retrofit in init migration); Task 7 coverage tests (test_llm.py, test_context_retrieval.py); Task 7 review PASS. Subtasks 1.1–1.7, 2.1–2.3, 3.1–3.4, 5.x, 6.x, 7.2–7.6 were already done.
- **State:** 135 tests passing; app-code coverage 82%. Last green commit: a95cc05 plus Task 7 header commit.
- **Next:** Only human-required subtasks remain: 1.8, 2.4, 2.5, 2.6, 3.5, 4.1. 4.2 and 4.3 are blocked behind 4.1.
- **Broken/open:** Task 7's reviewer noted commit 3eb89d5 (7.6) ran with the RLS tests ignored; rerun on HEAD was green. Whole-repo `--cov=.` reads 75% because evals/ and scripts/ are untested; backend/recommender/retrieval/app is 82%.
