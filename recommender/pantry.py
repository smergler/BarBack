"""Classification of non-bottle ingredients.

The grounding metric only polices *bottles* (the hallucination-prone items).
Everything else is either an always-on pantry staple or a perishable the user
may or may not have on hand.
"""

# Always assumed present; never flagged.
PANTRY_STAPLES = {
    "ice",
    "water",
    "sugar",
    "simple syrup",
    "demerara syrup",
    "rich simple syrup",
    "salt",
}

# Fresh staples that vary day to day. Surfaced as a shopping-list note, never
# counted against grounding. The request can declare which are on hand.
PERISHABLE_STAPLES = {
    "lemon",
    "lime",
    "orange",
    "grapefruit",
    "citrus",
    "lemon juice",
    "lime juice",
    "orange juice",
    "grapefruit juice",
    "lemon peel",
    "orange peel",
    "lemon twist",
    "orange twist",
    "egg white",
    "egg",
    "mint",
    "basil",
    "rosemary",
    "thyme",
}


def normalize(name: str) -> str:
    return " ".join(name.lower().strip().replace(".", "").split())


def is_pantry(name: str) -> bool:
    return normalize(name) in PANTRY_STAPLES


def is_perishable(name: str) -> bool:
    n = normalize(name)
    if n in PERISHABLE_STAPLES:
        return True
    # tolerate "fresh lime juice", "orange twist", etc.
    return any(p in n for p in PERISHABLE_STAPLES)
