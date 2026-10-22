# Known Issues

## drink_ids fallback in frontend (app/static/index.html)

Task 6.3 replaced positional guessing with `drink_ids[i]` from the `/recommend` response,
but kept a silent fallback:

```js
const id = (drink_ids && drink_ids[i]) || sessionDrinks[priorDrinks.length + i]?.id;
```

If `create_session_drinks` returns an empty list (Supabase hiccup, network error, or mock
returning `[]`), `drink_ids` is `[]`, the fallback fires, and verdict buttons silently get
no `data-drink-id`. Clicks no-op with no error surfaced to the user.

**Fix:** surface an error if `drink_ids` length doesn't match `suggestions` length, rather
than falling back to positional guessing.

---

## Resolved: campari→amaro cross-identity substitution (fixed 2026-08-24)

`_CATEGORY_TERMS` in `recommender/inventory_match.py` used to map `"campari": {"amaro"}`,
so an ingredient literally named "Amaro Nonino" would match an owned Campari — a
cross-identity false positive that inflated the grounding metric. Removed the substitution
(Task 1.1), keeping `"amaro": {"amaro"}` as the only amaro entry, and added
`test_campari_does_not_match_generic_amaro` (Task 1.2) to prevent regression.

## Resolved: dead gin/rum/vodka/tequila category-fallback branches (fixed 2026-08-24)

`"rum"`, `"gin"`, `"vodka"`, `"tequila"` were stripped by `_STOPWORDS` before ever reaching
the `_CATEGORY_TERMS` fallback that already listed them as keys, so a bare "gin"/"rum"/
"vodka"/"tequila" ingredient reference could never match by category — the same treatment
`bourbon`/`rye`/`mezcal` already got exempted from. Un-stripped the four terms (Task 1.3)
and added `test_gin_rum_vodka_tequila_category_fallback` (Task 1.4), verified to fail on
the pre-fix code.

## Ambiguous category match in `match_bottle` (recommender/inventory_match.py)

The `_CATEGORY_TERMS` fallback returns the first bottle whose `category` matches — no
tie-breaking, no preference for closer name matches. A user with two bourbons (e.g. Four
Roses + Buffalo Trace) asking for "bourbon" gets whichever iterates first. The grounding
scorer calls it correct either way, so this is invisible in evals but wrong in real usage.

**Fix:** ID-constraining the model is the right lever (already on PLAN_EXTEND). Until then,
if multiple bottles match a category fallback, prefer the one with the highest name-token
overlap with the ingredient string rather than iteration order.

## Resolved: Supabase legacy API keys and HS256 JWT secret (fixed 2026-10-21)

Migrated to Supabase publishable/secret API keys and JWKS-only verification. SUPABASE_JWT_TOKEN misnomer resolved by removal.
