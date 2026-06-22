# Prompt: LLM-Powered Recommendation Endpoint

Implement the `/recommend` endpoint and the LLM service for the drink suggester app.

**POST /recommend** — accepts:
```json
{
  "occasion": "movie night",
  "mood": "cozy and relaxed",
  "companion_ids": ["uuid1", "uuid2"],
  "count": 3,
  "constraints": ["no sweet drinks", "something stirred"]
}
```

Returns:
```json
{
  "suggestions": [
    {
      "name": "Mole Old Fashioned",
      "description": "A spirit-forward riff on the classic with chocolate and spice notes",
      "recipe": "2oz Four Roses Small Batch, 1 tsp demerara syrup, 2 dashes Bittermens Xocolatl Mole Bitters...",
      "why": "Your wife loves spirit-forward drinks and you have all the ingredients",
      "ingredients_needed": ["Four Roses Small Batch", "demerara syrup", "Bittermens Xocolatl Mole Bitters"],
      "missing_ingredients": []
    }
  ]
}
```

**Pre-filtering logic (services/recommender.py) — do this BEFORE calling the LLM:**
1. Load the user's active inventory from DB
2. Load companion profiles for the given companion_ids
3. Build a "dislike set" — union of all companions' dislikes
4. Build a "preference set" — union of all companions' likes
5. Filter inventory to relevant spirit categories for the occasion
6. Build a focused context string: available bottles (name + category), companion preferences, constraints, occasion

**LLM service (services/llm.py):**
- Use the `anthropic` Python library
- Model: `claude-haiku-4-5-20251001` (fast and cheap)
- System prompt: You are a skilled bartender with deep knowledge of cocktails. You make recommendations based only on spirits the user has available. You never suggest ingredients the user doesn't have unless you flag them as "missing_ingredients". Be specific about recipes with exact quantities.
- User message: the focused context built by the pre-filter
- Parse the JSON response (ask the model to respond in JSON)
- Use `max_tokens=1000`, `temperature=0.7`

Handle cases where the model returns malformed JSON gracefully — retry once, then return a 500 with a helpful message.
