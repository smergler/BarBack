# BUILD_LOG — PLAN_PROTECT.md attempt journal

Append-only. Newest at the bottom.
Format: attempted → failed → suspected cause → now doing.

<!-- entries below -->

## [Task 3.2] _WEAK_TOKENS: excluded "dry" and "sweet" — 2026-07-03
- **Tried:** Implementing _WEAK_TOKENS per plan spec, which lists `orange, lemon, lime, dry, sweet, spiced, aged, white, blanco`
- **Failed:** Adding "sweet" and "dry" breaks existing test `test_generic_name_matches_owned_specific_bottle` — "sweet vermouth" matching "Carpano Antica Sweet Vermouth" and "dry vermouth" matching "Dolin Dry Vermouth" both depend on these single tokens carrying the match (since "vermouth" is a stopword). Blocking them as weak tokens removes vermouth subcategory disambiguation.
- **Suspected cause:** [plan] — "dry" and "sweet" serve double duty as vermouth subcategory qualifiers and as fruit/adjective modifiers. The plan lists them as weak tokens without accounting for the vermouth case.
- **Now doing:** _WEAK_TOKENS = `{orange, lemon, lime, white, blanco, spiced, aged}` — omitting "dry" and "sweet". The false-positive case the plan targets (orange bitters vs Orange Curaçao) is covered. Existing vermouth matching tests continue to pass.
