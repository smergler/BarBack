"""Free-form matching of an ingredient name to an owned bottle.

This fuzzy layer exists *because* we let the model name bottles freely. It is
exactly the code that ID-constraining the model would later make unnecessary —
the planned lever for pushing grounding rate up.
"""

from __future__ import annotations

from .pantry import normalize
from .schemas import Bottle


def _tokens(s: str) -> set[str]:
    return set(normalize(s).split())


# Tokens too generic to carry a match on their own. Generic category nouns are
# included so "Peychaud's Bitters" does NOT match an owned "Angostura Bitters"
# on the shared word "bitters" — the brand/qualifier token must overlap instead.
# (Subcategory words like bourbon/rye/mezcal are intentionally NOT here, so a
# recipe calling for generic "rye" still matches an owned "Rittenhouse Rye".)
_STOPWORDS = {
    "the", "of", "and", "small", "batch", "bottle",
    "bitters", "vermouth", "liqueur", "syrup",
    "whiskey", "whisky", "brandy", "cognac",
}

# Generic fruit/flavor tokens that alone cannot confirm a match. Prevents
# "orange bitters" matching "Orange Curaçao" on the shared "orange" token alone.
# Note: "sweet" and "dry" are intentionally excluded — they are genuine
# subcategory qualifiers for vermouth (sweet vs dry) and must carry a match.
_WEAK_TOKENS = {"orange", "lemon", "lime", "white", "blanco", "spiced", "aged"}

# Maps ingredient category words → Bottle.category (or subcategory) values.
# Used as a fallback when no name-token overlap is found. Lets a recipe calling
# for a generic "bourbon" match an owned "Four Roses Small Batch" via category.
_CATEGORY_TERMS: dict[str, set[str]] = {
    "bourbon": {"bourbon"},
    "rye": {"rye"},
    "mezcal": {"mezcal"},
    "tequila": {"tequila"},
    "gin": {"gin"},
    "rum": {"rum"},
    "vodka": {"vodka"},
    "amaro": {"amaro"},
}


def match_bottle(ingredient_name: str, inventory: list[Bottle]) -> Bottle | None:
    ing = _tokens(ingredient_name) - _STOPWORDS
    if not ing:
        return None
    best: tuple[float, Bottle] | None = None
    for b in inventory:
        bt = _tokens(b.name) - _STOPWORDS
        if not bt:
            continue
        overlap = ing & bt
        if not overlap:
            continue
        # Skip matches where every overlapping token is a weak flavor word —
        # they don't distinguish the bottle type, only a modifier.
        if overlap.issubset(_WEAK_TOKENS):
            continue
        # fraction of the smaller token set that overlaps
        score = len(overlap) / min(len(ing), len(bt))
        if score >= 0.5 and (best is None or score > best[0]):
            best = (score, b)

    if best:
        return best[1]

    # Category fallback: only for genuinely generic asks, where every remaining
    # token is itself a category word (e.g. "bourbon", "gin"). A specific
    # product name like "Amaro Nonino" has a non-category token ("nonino") and
    # must not fall back to a same-category bottle of a different identity
    # (e.g. an owned Campari).
    if ing <= _CATEGORY_TERMS.keys():
        for term in sorted(ing):
            target_cats = _CATEGORY_TERMS[term]
            for b in inventory:
                if b.category in target_cats or (b.subcategory and b.subcategory in target_cats):
                    return b

    return None
