"""Fetch all available cocktails from TheCocktailDB free API.

Strategy: combine two discovery methods to maximize coverage on the free tier.
  1. Search by first letter (a-z) — up to 25 per letter
  2. Filter by category — up to 100 per category
Then look up any IDs found via (2) that weren't returned by (1).

    python -m scripts.fetch_cocktaildb
"""

from __future__ import annotations

import json
import string
import time
from pathlib import Path

import httpx

OUTPUT = Path("data/cocktails.json")
BASE = "https://www.thecocktaildb.com/api/json/v1/1"
CATEGORIES = ["Cocktail", "Ordinary Drink", "Shot", "Punch / Party Drink", "Shake", "Cocoa", "Coffee / Tea"]


def _parse_ingredients(drink: dict) -> list[dict]:
    ingredients = []
    for i in range(1, 16):
        name = (drink.get(f"strIngredient{i}") or "").strip()
        measure = (drink.get(f"strMeasure{i}") or "").strip()
        if name:
            ingredients.append({"name": name, "measure": measure or None})
    return ingredients


def _normalize(d: dict) -> dict:
    return {
        "id": d["idDrink"],
        "name": d["strDrink"],
        "category": d.get("strCategory") or None,
        "alcoholic": d.get("strAlcoholic") or None,
        "glass": d.get("strGlass") or None,
        "instructions": (d.get("strInstructions") or "").strip() or None,
        "ingredients": _parse_ingredients(d),
    }


def main() -> None:
    client = httpx.Client(timeout=10)
    cocktails: dict[str, dict] = {}

    # Phase 1: letter search
    print("Phase 1: letter search (a-z)...")
    for letter in string.ascii_lowercase:
        resp = client.get(f"{BASE}/search.php", params={"f": letter})
        resp.raise_for_status()
        for d in (resp.json().get("drinks") or []):
            cocktails[d["idDrink"]] = _normalize(d)
        print(f"  {letter}: {len(resp.json().get('drinks') or [])} drinks  (total {len(cocktails)})")
        time.sleep(0.1)

    # Phase 2: category filter — collect IDs we haven't seen
    print(f"\nPhase 2: category filter for new IDs...")
    new_ids: set[str] = set()
    for cat in CATEGORIES:
        resp = client.get(f"{BASE}/filter.php", params={"c": cat})
        resp.raise_for_status()
        for d in (resp.json().get("drinks") or []):
            if d["idDrink"] not in cocktails:
                new_ids.add(d["idDrink"])
        time.sleep(0.2)
    print(f"  Found {len(new_ids)} new IDs to look up")

    # Phase 3: look up each new ID individually
    if new_ids:
        print(f"\nPhase 3: looking up {len(new_ids)} new recipes...")
        for cid in sorted(new_ids):
            resp = client.get(f"{BASE}/lookup.php", params={"i": cid})
            resp.raise_for_status()
            drinks = resp.json().get("drinks") or []
            if drinks:
                cocktails[cid] = _normalize(drinks[0])
            time.sleep(0.15)
        print(f"  Done. Total: {len(cocktails)}")

    result = sorted(cocktails.values(), key=lambda c: c["name"])
    OUTPUT.write_text(json.dumps(result, indent=2, ensure_ascii=False))
    print(f"\nWrote {len(result)} cocktails to {OUTPUT}")


if __name__ == "__main__":
    main()
