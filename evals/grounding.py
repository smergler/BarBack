"""Deterministic grounding scorer — the primary eval metric.

A suggestion is *grounded* iff none of its ingredients makes a false claim about
availability:
  - source "inventory" must match a bottle the user owns,
  - source "pantry" must be an allowed always-on staple,
  - source "perishable" and "missing" are honest disclosures and never fail.

Grounding rate = grounded suggestions / total suggestions (per-suggestion binary).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from recommender.inventory_match import match_bottle
from recommender.pantry import is_pantry
from recommender.schemas import Bottle, IngredientSource, Suggestion


@dataclass
class IngredientCheck:
    name: str
    claimed: IngredientSource
    grounded: bool
    reason: str


@dataclass
class SuggestionCheck:
    name: str
    ingredient_checks: list[IngredientCheck] = field(default_factory=list)
    shopping_list: list[str] = field(default_factory=list)

    @property
    def violations(self) -> list[IngredientCheck]:
        return [c for c in self.ingredient_checks if not c.grounded]

    @property
    def grounded(self) -> bool:
        return not self.violations


def check_suggestion(s: Suggestion, inventory: list[Bottle]) -> SuggestionCheck:
    result = SuggestionCheck(name=s.name)
    for ing in s.ingredients:
        src = ing.source
        if src == IngredientSource.inventory:
            if match_bottle(ing.name, inventory):
                result.ingredient_checks.append(
                    IngredientCheck(ing.name, src, True, "owned bottle")
                )
            else:
                result.ingredient_checks.append(
                    IngredientCheck(
                        ing.name, src, False,
                        "claimed inventory but no matching bottle (hallucinated ownership)",
                    )
                )
        elif src == IngredientSource.pantry:
            if is_pantry(ing.name):
                result.ingredient_checks.append(
                    IngredientCheck(ing.name, src, True, "pantry staple")
                )
            else:
                result.ingredient_checks.append(
                    IngredientCheck(
                        ing.name, src, False,
                        "claimed pantry but not an allowed staple (assumes an item you may lack)",
                    )
                )
        elif src == IngredientSource.perishable:
            result.ingredient_checks.append(
                IngredientCheck(ing.name, src, True, "perishable (not policed)")
            )
            result.shopping_list.append(ing.name)
        else:  # missing
            result.ingredient_checks.append(
                IngredientCheck(ing.name, src, True, "declared missing (honest)")
            )
            result.shopping_list.append(ing.name)
    return result


@dataclass
class GroundingReport:
    suggestion_checks: list[SuggestionCheck]

    @property
    def total(self) -> int:
        return len(self.suggestion_checks)

    @property
    def grounded(self) -> int:
        return sum(1 for c in self.suggestion_checks if c.grounded)

    @property
    def rate(self) -> float:
        return self.grounded / self.total if self.total else 0.0


def score(suggestions: list[Suggestion], inventory: list[Bottle]) -> GroundingReport:
    return GroundingReport([check_suggestion(s, inventory) for s in suggestions])
