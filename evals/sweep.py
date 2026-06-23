"""Multi-model sweep: run all eval scenarios across Haiku/Sonnet/Opus and print a comparison table.

    python -m evals.sweep              # runs all three models (costs ~$0.05)
    python -m evals.sweep --judge      # include LLM-as-judge dimensions
    python -m evals.sweep --models haiku sonnet   # subset

Live mode always — reads ANTHROPIC_API_KEY from the environment or a .env file.
"""

from __future__ import annotations

import argparse
import os
import time

from dotenv import load_dotenv

from evals.fixtures import SCENARIOS
from evals.grounding import score
from evals.judge import judge_suggestion, summarize
import evals.makeable as makeable_mod
from recommender.llm import AnthropicClient
from recommender.recommender import recommend

# Price per million tokens (input, output) as of 2026-06
PRICE_TABLE: dict[str, tuple[float, float]] = {
    "claude-haiku-4-5-20251001": (1.00, 5.00),
    "claude-haiku-4-5": (1.00, 5.00),
    "claude-sonnet-4-6": (3.00, 15.00),
    "claude-opus-4-8": (5.00, 25.00),
    "claude-opus-4-7": (5.00, 25.00),
    "claude-opus-4-6": (5.00, 25.00),
}

MODEL_SHORTHANDS = {
    "haiku": "claude-haiku-4-5-20251001",
    "sonnet": "claude-sonnet-4-6",
    "opus": "claude-opus-4-8",
}

DEFAULT_MODELS = ["claude-haiku-4-5-20251001", "claude-sonnet-4-6", "claude-opus-4-8"]


def _resolve_model(name: str) -> str:
    return MODEL_SHORTHANDS.get(name, name)


def _cost(model: str, in_tok: int, out_tok: int) -> float:
    in_p, out_p = PRICE_TABLE.get(model, (5.00, 25.00))
    return (in_tok * in_p + out_tok * out_p) / 1_000_000


def run_model(model_id: str, run_judge: bool) -> dict:
    total = grounded = mk_total = mk_uses_inv = mk_now = 0
    in_tok = out_tok = 0
    all_verdicts = []
    t0 = time.perf_counter()

    for sc in SCENARIOS:
        llm = AnthropicClient(model=model_id)
        rec = recommend(sc.request, sc.inventory, llm)

        if llm.last_usage:
            in_tok += llm.last_usage.input_tokens
            out_tok += llm.last_usage.output_tokens

        report = score(rec.suggestions, sc.inventory)
        total += report.total
        grounded += report.grounded

        if sc.open_ended:
            mk = makeable_mod.score(rec.suggestions, sc.inventory)
            mk_total += mk.total
            mk_uses_inv += mk.uses_inventory_count
            mk_now += mk.makeable_now_count

        if run_judge:
            judge_llm = AnthropicClient(model=model_id)
            for s in rec.suggestions:
                verdict = judge_suggestion(s, sc.request, judge_llm)
                all_verdicts.append(verdict)
                if judge_llm.last_usage:
                    in_tok += judge_llm.last_usage.input_tokens
                    out_tok += judge_llm.last_usage.output_tokens

    elapsed = time.perf_counter() - t0
    grounding_rate = grounded / total if total else 0.0
    mk_rate = mk_uses_inv / mk_total if mk_total else 0.0
    mk_now_rate = mk_now / mk_total if mk_total else 0.0
    est_cost = _cost(model_id, in_tok, out_tok)

    result: dict = {
        "model": model_id,
        "grounding": grounding_rate,
        "makeable": mk_rate,
        "makeable_now": mk_now_rate,
        "in_tok": in_tok,
        "out_tok": out_tok,
        "cost_usd": est_cost,
        "elapsed_s": elapsed,
    }

    if all_verdicts:
        js = summarize(all_verdicts)
        result.update(
            {
                "constraints": js.constraint_pass_rate,
                "occasion_fit": js.avg_occasion_fit,
                "plausibility": js.avg_recipe_plausibility,
                "name_acc": js.name_accuracy_rate,
                "name_acc_n": js.name_accuracy_n,
                "judge_n": js.n,
            }
        )

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Multi-model eval sweep.")
    parser.add_argument(
        "--models",
        nargs="+",
        default=DEFAULT_MODELS,
        help="model ids or shorthands (haiku/sonnet/opus)",
    )
    parser.add_argument("--judge", action="store_true", help="include LLM-as-judge dimensions")
    args = parser.parse_args()

    load_dotenv()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        raise SystemExit("ANTHROPIC_API_KEY not set.")

    models = [_resolve_model(m) for m in args.models]
    print(f"Sweeping {len(models)} model(s) across {len(SCENARIOS)} scenarios...\n")

    results = []
    for mid in models:
        print(f"  running {mid}...", flush=True)
        r = run_model(mid, run_judge=args.judge)
        results.append(r)
        print(f"    grounding={r['grounding']:.0%}  cost=${r['cost_usd']:.4f}  elapsed={r['elapsed_s']:.1f}s")

    print()
    _print_table(results, include_judge=args.judge)


def _print_table(results: list[dict], include_judge: bool) -> None:
    cols = ["model", "ground%", "make%", "make-now%", "in_tok", "out_tok", "cost_$", "sec"]
    if include_judge:
        cols += ["constrain%", "occ_fit", "plaus", "name_acc%"]

    widths = [max(len(c), 12) for c in cols]
    widths[0] = max(len(r["model"]) for r in results) + 2

    header = "  ".join(f"{c:<{w}}" for c, w in zip(cols, widths))
    print(header)
    print("-" * len(header))

    for r in results:
        row = [
            r["model"],
            f"{r['grounding']:.0%}",
            f"{r['makeable']:.0%}",
            f"{r['makeable_now']:.0%}",
            str(r["in_tok"]),
            str(r["out_tok"]),
            f"{r['cost_usd']:.4f}",
            f"{r['elapsed_s']:.1f}",
        ]
        if include_judge:
            row += [
                f"{r.get('constraints', 0):.0%}" if "constraints" in r else "n/a",
                f"{r.get('occasion_fit', 0):.1f}" if "occasion_fit" in r else "n/a",
                f"{r.get('plausibility', 0):.1f}" if "plausibility" in r else "n/a",
                (
                    f"{r['name_acc']:.0%} ({r['name_acc_n']}/{r['judge_n']})"
                    if r.get("name_acc") is not None
                    else "n/a"
                ),
            ]
        print("  ".join(f"{v:<{w}}" for v, w in zip(row, widths)))


if __name__ == "__main__":
    main()
