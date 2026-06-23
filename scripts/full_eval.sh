#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")/.."

.venv/bin/python -m evals.run_evals \
  --live \
  --judge \
  --save-verdicts evals/judge_verdicts.json \
  --save-suggestions evals/suggestions.json
