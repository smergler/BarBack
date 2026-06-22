# Prompt / Reference: Mobile App API Contract

This file documents the API contract for building a React Native (or other) mobile app against the drink suggester backend.

**Base URL:** Set from environment (Railway URL)

**Auth:**
All requests require: `Authorization: Bearer <supabase_jwt_token>`
Get the token from Supabase Auth on the mobile side: `supabase.auth.getSession().data.session.access_token`

**Endpoints summary:**
```
GET    /inventory                 → list bottles (filter: ?category=bourbon)
POST   /inventory                 → add bottle {name, category, subcategory?, is_favorite?}
PUT    /inventory/:id             → update bottle
DELETE /inventory/:id             → soft-delete (marks out of stock)

GET    /companions                → list companions
POST   /companions                → create companion {name, relationship?, likes[], dislikes[]}
PUT    /companions/:id            → update
POST   /companions/:id/feedback   → {drink_name, verdict, descriptors[]}

GET    /sessions                  → list sessions (?limit=20)
POST   /sessions                  → create {title, occasion, companion_ids[], session_date?}
GET    /sessions/:id              → session + drinks
POST   /sessions/:id/drinks       → add drink {name, recipe, verdict, was_suggested_by_ai}

POST   /recommend                 → {occasion, mood, companion_ids[], count?, constraints?[]}
```

**Response conventions:**
- 200 OK with data on success
- 201 Created with new object on POST
- 400 Bad Request with `{error: "message"}` on validation failure
- 401 Unauthorized when token missing/invalid
- 403 Forbidden when resource belongs to another user
- 404 Not Found when resource doesn't exist
- 500 Internal Server Error with `{error: "message", detail?: "..."}`

**Pagination:** GET /sessions and GET /inventory support `?limit=N&offset=N`

**Recommended mobile stack:** React Native + Expo, using `@supabase/supabase-js` for auth and `@tanstack/react-query` for API calls — same patterns as the web frontend.
