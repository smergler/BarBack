# Drink Suggester

An LLM cocktail recommender **grounded in the user's actual bottle inventory**, built
eval-first: the centerpiece is a measurement harness that proves the recommendations only
use ingredients you own (or honestly flags what you'd need to buy), not just a model call.

> Built as an AI/ML portfolio piece. The interesting engineering is the discipline *around*
> the LLM — grounding metrics, adversarial evals, an LLM-as-judge — not the model call itself.

## What it does

Given an occasion, mood, optional companions, and constraints, it recommends cocktails it
can actually make from a known inventory. Every ingredient is labeled `inventory` (owned),
`pantry` (staple), `perishable` ("grab this"), or `missing` (specialty item you lack) — so
the system can be scored on whether it's honest about what you have.

## Why it's interesting (the eval-first angle)

The recommender is graded by a measurement harness, not vibes:

- **Grounding rate** (deterministic) — % of suggestions where every ingredient is owned,
  an allowed staple, or honestly flagged. Set math, not NLP.
- **Makeable rate** (deterministic, planned) — does the drink actually use owned bottles,
  or is it a shopping list?
- **LLM-as-judge** — the subjective dimensions (constraint adherence, occasion fit,
  recipe plausibility) deterministic checks can't see.

See [`docs/eval-spec.md`](docs/eval-spec.md) for exact definitions and
[`RESUME_STORY.md`](RESUME_STORY.md) for the metrics timeline and engineering decisions.

## Architecture (current)

```
RecommendRequest ─▶ pre-filter / context build ─▶ Claude (structured output)
                                                        │
                                                        ▼
                                         parse + validate (Pydantic)
                                                        │
                          ┌─────────────────────────────┼───────────────────────┐
                          ▼                             ▼                         ▼
                  grounding scorer            makeable scorer (planned)      LLM judge
                  (deterministic)              (deterministic)              (subjective)
```

The recommender core (`recommender/`) is framework-agnostic — no web/DB dependencies — so
it can be developed and evaluated in isolation, then lifted into a backend later.

## Layout

```
recommender/   core: schemas, pantry rules, bottle matcher, LLM client, context, orchestrator
evals/         fixtures, mock responses, grounding scorer, LLM judge, runner, inspect tool
tests/         pytest unit tests (scorers, matcher, parser, judge)
docs/          eval-spec.md, adr-001-data-isolation.md
PLAN.md        build plan (atomic, status-tracked subtasks) for current + future work
RESUME_STORY.md  narrative, metrics timeline, key decisions
```

## Setup

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install pytest          # for the test suite
```

For live model calls, create a `.env` at the project root (see `env.template`):

```
ANTHROPIC_API_KEY=sk-ant-...
```

## Run

```bash
.venv/bin/python -m pytest -q                       # unit tests
.venv/bin/python -m evals.run_evals                 # offline eval (mock responses, no tokens)
.venv/bin/python -m evals.run_evals --live          # eval against the real model
.venv/bin/python -m evals.run_evals --live --judge  # + LLM judge
.venv/bin/python -m evals.inspect <scenario_id>...  # print actual suggestions for a scenario
```

## Status

Recommender core + grounding eval + LLM judge are implemented and tested (offline and
live). Live grounding is currently 100% across the scenario set, including adversarial
named-classics. Next up (`PLAN.md`): a makeable-rate metric, a live judge run, then a
thin deployable slice. _A live demo link will go here once deployed._
