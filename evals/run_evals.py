"""Run every scenario through the recommender and report grounding rate.

    python -m evals.run_evals

Uses MockClient by default (offline, zero tokens). Swap in AnthropicClient once
an API key is available to measure the *live* model's grounding rate.
"""

from __future__ import annotations

from evals.fixtures import SCENARIOS
from evals.grounding import score
from evals.mock_responses import MOCK_RESPONSES
from recommender.llm import MockClient
from recommender.recommender import recommend


def main() -> None:
    total = 0
    grounded = 0
    property_failures: list[str] = []

    header = f"{'scenario':<22}{'sugg':>5}{'grounded':>10}   violations"
    print(header)
    print("-" * len(header) * 2)

    for sc in SCENARIOS:
        llm = MockClient(MOCK_RESPONSES, key=sc.id)
        rec = recommend(sc.request, sc.inventory, llm)
        report = score(rec.suggestions, sc.inventory)
        total += report.total
        grounded += report.grounded

        viol = [
            f"{c.name}: {v.name}({v.claimed.value})"
            for c in report.suggestion_checks
            for v in c.violations
        ]
        viol_str = "; ".join(viol) if viol else "—"
        print(f"{sc.id:<22}{report.total:>5}{report.grounded:>7}/{report.total:<2}   {viol_str}")

        # property assertions
        if sc.expect_count is not None and report.total != sc.expect_count:
            property_failures.append(
                f"{sc.id}: expected {sc.expect_count} suggestions, got {report.total}"
            )
        if sc.expect_min_grounded_rate is not None and report.rate < sc.expect_min_grounded_rate:
            property_failures.append(
                f"{sc.id}: grounding {report.rate:.0%} < expected {sc.expect_min_grounded_rate:.0%}"
            )

    rate = grounded / total if total else 0.0
    print("-" * len(header) * 2)
    print(f"GROUNDING RATE: {grounded}/{total} = {rate:.0%}")

    if property_failures:
        print(f"\nPROPERTY FAILURES ({len(property_failures)}):")
        for f in property_failures:
            print(f"  ✗ {f}")
    else:
        print("\nAll property assertions passed.")


if __name__ == "__main__":
    main()
