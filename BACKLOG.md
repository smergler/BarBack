# BACKLOG

Unscheduled ideas. Not plans: nothing here is run by `/build` until it is turned into a `plans/<slug>/PLAN.md`.

## 1. Organize plans into per-plan folders with a derived status
**Status:** done on branch `loop/barback-reorg-plan-files` (2026-10-14): plans moved to `plans/<slug>/`, logs split per plan, `plans/STATUS.md` generated from checkboxes, `/build`, `/plan` and `/kickoff` updated.

## 2. Research spike: token savings beyond EXTEND Task 4
**Type:** spike. Output is a short findings doc plus a go/no-go list, not code.
**Scope rule:** only investigate what `plans/extend/PLAN.md` Task 4 does not already cover. Task 4 = batch the judge per scenario + `cache_control` on the system prompt, measured with `evals/trace_summary.py`.
Questions to answer:
- Production `/recommend` path: how many input tokens per call? `SYSTEM_PROMPT` plus the inventory dominate. Is caching worth it at real traffic, given the 5-minute cache TTL?
- Context size: does `build_context` send fields the model doesn't need (full inventory every call, empty sections)?
- Model choice: the sweep in `RESUME_STORY.md` already compares models on cost. Is any cheaper model good enough on the scenarios that matter?
- Output side: `max_tokens` (2000) and suggestion count vs actual output lengths in `evals/traces.jsonl`.
- Eval cost: which runs actually spend the most (live scenarios, judge, calibration, nightly)? Is the nightly run worth running daily?
Baseline: `evals/traces.jsonl` and the per-model cost table in `RESUME_STORY.md`. Take the measurement before Task 4 lands, so Task 4's delta is clean.
Exit criteria: for each question, either a measured number or "not worth pursuing, because X".

## 3. Per-step commit history
Derive plan -> subtask -> commit from `git log`, so each plan's history shows which commit completed each step.
- Blocker: the `[Task X.Y]` prefix is shared by PROTECT and HARDEN (both numbered Tasks 1-7), so it needs a date range or a branch per plan to disambiguate.
- Human-only steps have no commit: record the date and outcome instead.
- Follows from item 1 (the per-plan folders).

## Run order (as of 2026-10-14)
1. ~~PLAN_HARDEN~~: merged (PRs #1, #2). Its human steps 2.4-2.6 moved into supabase-keys Task 6.
2. `plans/supabase-keys/PLAN.md` (tasks 1-5, then the human rollout in task 6).
3. ~~Backlog item 1~~: reorganization (this branch). Per-step commit history still open (item 3).
4. Backlog item 2: token-savings spike. Measure the baseline here, before EXTEND Task 4.
5. `plans/extend/PLAN.md`, in task order 1, 2, 4, 3, 5.
